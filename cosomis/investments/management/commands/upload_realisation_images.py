# investments/management/commands/upload_realisation_images.py
"""
Walk the realisation images folder, upload each file to MinIO (bucket: ldp),
and create Attachment records linked to the resolved village.

Folder structure expected:
    <root>/<département>/<commune>/<arrondissement>/<village>/<sub_component>/[subfolder/]<files>

Files placed directly under <village>/ (depth 4, no sub_component) are skipped
and reported as anomalies.

Usage:
    python manage.py upload_realisation_images --dir images_realisation_sous-projets_15062026
    python manage.py upload_realisation_images --dir ... --dry-run
"""
import os
import re

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from administrativelevels.utils.resolvers import resolve_adm_level
from investments.models import Attachment

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif",
    ".webp", ".bmp", ".tiff",
}

DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls",
    ".xlsx", ".ppt", ".pptx", ".txt",
}

VALID_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS


def _normalize_sub_component(raw):
    """Normalize sub-component folder name to DB values: 1.2-b -> 1.2b etc."""
    return re.sub(r"[-\s]", "", raw.lower())


def _attachment_type(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTENSIONS:
        return Attachment.PHOTO
    return Attachment.DOCUMENT


def _get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=getattr(settings, "AWS_S3_ENDPOINT_URL", None),
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )


def _ensure_bucket(s3, bucket):
    """Create the bucket if it does not already exist."""
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
        else:
            raise


class Command(BaseCommand):
    help = (
        "Upload realisation images/documents to MinIO and create "
        "Attachment records linked to the resolved village."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            required=True,
            help="Root folder containing the realisation images "
                 "(structured as département/commune/arrondissement/village/sub_component/).",
        )
        parser.add_argument(
            "--bucket",
            default="ldp",
            help="MinIO bucket name (default: ldp).",
        )
        parser.add_argument(
            "--proxy-prefix",
            default="",
            help=(
                "URL prefix prepended to the MinIO object URL when storing "
                "in the Attachment.url field. "
                "Example: https://cdd.coso.gouv.bj/fr/facilitators/serve-minio-file/ "
                "Leave empty to store the raw MinIO URL (useful for local testing)."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate without uploading files or writing to the database.",
        )

    def handle(self, *args, **options):
        root_dir     = options["dir"]
        bucket       = options["bucket"]
        proxy_prefix = options["proxy_prefix"].rstrip("/")
        dry_run      = options["dry_run"]

        if not os.path.isdir(root_dir):
            raise CommandError(f"Directory not found: {root_dir}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "*** DRY RUN — no files will be uploaded, no DB records created ***"
            ))

        # --- MinIO client + bucket ---
        s3 = _get_s3_client()
        endpoint = getattr(
            settings, "AWS_S3_ENDPOINT_URL",
            f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"
        )

        if not dry_run:
            _ensure_bucket(s3, bucket)
            self.stdout.write(f"Bucket '{bucket}' ready.")

        # --- Counters ---
        total_files      = 0
        uploaded         = 0
        skipped_adm      = 0   # could not resolve administrative level
        skipped_ext      = 0   # unsupported extension
        skipped_no_sub   = 0   # valid file but no sub_component folder (depth 4)
        skipped_existing = 0   # file already uploaded (idempotence)
        no_sub_files     = []  # paths of anomalous files for reporting
        errors           = 0
        adm_cache        = {}  # (dept, com, arr, vil) -> AdministrativeLevel | None

        # Pre-load existing URLs to avoid DB query per file
        existing_urls = set(
            Attachment.objects.filter(source="realisation_upload")
            .values_list("url", flat=True)
        )

        # First pass: count total valid files
        for dp, dirs, files in os.walk(root_dir):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in VALID_EXTENSIONS:
                    total_files += 1

        self.stdout.write(f"Total files to process: {total_files}")

        attachments_to_create = []

        for dirpath, dirnames, filenames in os.walk(root_dir):
            if not filenames:
                continue

            rel   = os.path.relpath(dirpath, root_dir)
            parts = rel.split(os.sep) if rel != "." else []
            depth = len(parts)

            # depth 4 = files directly under village/ — no sub_component
            if depth == 4:
                for filename in filenames:
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in VALID_EXTENSIONS:
                        skipped_no_sub += 1
                        no_sub_files.append(os.path.join(dirpath, filename))
                continue

            # Files only processed at depth >= 5
            if depth < 5:
                continue

            dept_name = parts[0]
            com_name  = parts[1]
            arr_name  = parts[2]
            vil_name  = parts[3]
            sub_raw   = parts[4]
            sub_comp  = _normalize_sub_component(sub_raw)

            # Resolve administrative chain (cached)
            cache_key = (dept_name, com_name, arr_name, vil_name)
            if cache_key not in adm_cache:
                dept = resolve_adm_level(dept_name, "département")
                com  = resolve_adm_level(com_name,  "commune",        parent=dept)
                arr  = resolve_adm_level(arr_name,  "arrondissement", parent=com)
                vil  = resolve_adm_level(vil_name,  "village",        parent=arr)
                adm_cache[cache_key] = vil
                if not vil:
                    self.stdout.write(self.style.WARNING(
                        f"  [UNRESOLVED] {dept_name} / {com_name} / "
                        f"{arr_name} / {vil_name}"
                    ))

            village = adm_cache[cache_key]

            for filename in filenames:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in VALID_EXTENSIONS:
                    skipped_ext += 1
                    continue

                if not village:
                    skipped_adm += 1
                    continue

                filepath   = os.path.join(dirpath, filename)
                object_key = f"realisation/village_{village.id}/{sub_comp}/{filename}"
                minio_url  = f"{endpoint}/{bucket}/{object_key}"
                stored_url = f"{proxy_prefix}/{minio_url}" if proxy_prefix else minio_url

                # Idempotence — skip if already uploaded
                if stored_url in existing_urls:
                    skipped_existing += 1
                    continue

                if dry_run:
                    uploaded += 1
                    continue

                # Check MinIO — skip if object already exists
                try:
                    s3.head_object(Bucket=bucket, Key=object_key)
                    skipped_existing += 1
                    continue
                except ClientError as e:
                    if e.response["Error"]["Code"] != "404":
                        self.stdout.write(self.style.ERROR(
                            f"  [ERROR] head_object {object_key}: {e}"
                        ))
                        errors += 1
                        continue
                    # 404 = does not exist yet, proceed with upload

                # Upload
                try:
                    with open(filepath, "rb") as fh:
                        s3.upload_fileobj(fh, bucket, object_key)
                    uploaded += 1
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(
                        f"  [ERROR] {filepath}: {exc}"
                    ))
                    errors += 1
                    continue

                attachments_to_create.append(
                    Attachment(
                        adm=village,
                        investment=None,
                        task=None,
                        url=stored_url,
                        type=_attachment_type(filename),
                        process_moment=Attachment.COMPLETED_INFRASTRUCTURE,
                        name=filename,
                        description=f"{sub_comp} — {vil_name}",
                        source="realisation_upload",
                    )
                )

        # --- Bulk create Attachment records ---
        if not dry_run and attachments_to_create:
            with transaction.atomic():
                Attachment.objects.bulk_create(
                    attachments_to_create, batch_size=500
                )

        # --- Summary ---
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY RUN] ' if dry_run else ''}Done."
        ))
        self.stdout.write(f"  Total files found          : {total_files}")
        self.stdout.write(f"  Uploaded                   : {uploaded}")
        self.stdout.write(f"  Skipped (unresolved adm)   : {skipped_adm}")
        self.stdout.write(f"  Skipped (bad extension)    : {skipped_ext}")
        self.stdout.write(
            f"  Skipped (already uploaded) : {skipped_existing}"
        )
        self.stdout.write(
            f"  Skipped (no sub_component) : {skipped_no_sub}"
            + (" ⚠️  see details below" if skipped_no_sub else "")
        )
        self.stdout.write(f"  Errors                     : {errors}")
        if not dry_run:
            self.stdout.write(
                f"  Attachment records created : {len(attachments_to_create)}"
            )

        if no_sub_files:
            self.stdout.write(self.style.WARNING(
                "\n  Files skipped — placed directly under village/ "
                "(missing sub_component folder):"
            ))
            for path in no_sub_files:
                self.stdout.write(f"    {path}")
