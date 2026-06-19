# investments/management/commands/setup_ldp_bucket.py
"""
Create the ldp MinIO bucket (if it does not exist) and apply a public-read
policy so that stored files can be served directly via their URL without
requiring signed credentials.

Run this once before upload_realisation_images:
    python manage.py setup_ldp_bucket
    python manage.py setup_ldp_bucket --dry-run
"""
import json

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


# Public-read bucket policy: allows anyone to GET any object in the bucket.
PUBLIC_READ_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicRead",
            "Effect": "Allow",
            "Principal": "*",
            "Action": ["s3:GetObject"],
            "Resource": ["{bucket_arn}/*"],
        }
    ],
}


class Command(BaseCommand):
    help = (
        "Create the ldp MinIO bucket and set a public-read policy. "
        "Run once before upload_realisation_images."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--bucket",
            default="ldp",
            help="Bucket name to create and configure (default: ldp).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Check connectivity and bucket status without making changes.",
        )

    def handle(self, *args, **options):
        bucket  = options["bucket"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "*** DRY RUN — no changes will be made ***"
            ))

        endpoint = getattr(settings, "AWS_S3_ENDPOINT_URL", None)
        if not endpoint:
            raise CommandError(
                "AWS_S3_ENDPOINT_URL is not set in settings. "
                "Add S3_ENDPOINT_URL to your .env and settings.py."
            )

        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

        self.stdout.write(f"Endpoint : {endpoint}")
        self.stdout.write(f"Bucket   : {bucket}")

        # --- Check connectivity ---
        try:
            s3.list_buckets()
            self.stdout.write(self.style.SUCCESS("Connection OK."))
        except ClientError as e:
            raise CommandError(f"Cannot connect to MinIO: {e}")

        # --- Check / create bucket ---
        bucket_exists = False
        try:
            s3.head_bucket(Bucket=bucket)
            bucket_exists = True
            self.stdout.write(f"Bucket '{bucket}' already exists.")
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                bucket_exists = False
                self.stdout.write(f"Bucket '{bucket}' does not exist — will create.")
            else:
                raise CommandError(f"Error checking bucket: {e}")

        if not dry_run and not bucket_exists:
            s3.create_bucket(Bucket=bucket)
            self.stdout.write(self.style.SUCCESS(f"Bucket '{bucket}' created."))

        # --- Apply public-read policy ---
        bucket_arn = f"arn:aws:s3:::{bucket}"
        policy = json.dumps(
            {
                **PUBLIC_READ_POLICY,
                "Statement": [
                    {
                        **s,
                        "Resource": [r.format(bucket_arn=bucket_arn) for r in s["Resource"]],
                    }
                    for s in PUBLIC_READ_POLICY["Statement"]
                ],
            }
        )

        if dry_run:
            self.stdout.write("Policy that would be applied:")
            self.stdout.write(policy)
        else:
            try:
                s3.put_bucket_policy(Bucket=bucket, Policy=policy)
                self.stdout.write(self.style.SUCCESS(
                    f"Public-read policy applied to bucket '{bucket}'."
                ))
            except ClientError as e:
                raise CommandError(f"Failed to apply bucket policy: {e}")

        # --- Summary ---
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "[DRY RUN] Done — no changes were made."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Done. Bucket '{bucket}' is ready with public-read access.\n"
                f"Files will be accessible at: {endpoint}/{bucket}/<object_key>"
            ))
