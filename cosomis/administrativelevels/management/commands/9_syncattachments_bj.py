from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel, Task
from investments.models import Attachment


class Command(BaseCommand):
    help = "Extract attachments from task documents and save them to the SQL database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without modifying the database"
        )

    def check_for_valid_facilitator(self, facilitator):
        """
        Returns True for production facilitators.

        Facilitators are excluded only when:
        - develop_mode is True
        - training_mode is True

        Missing fields are treated as False.
        """
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })

        for document in db:
            develop_mode = document.get("develop_mode", False)
            training_mode = document.get("training_mode", False)

            return not (develop_mode or training_mode)

        # No facilitator document found
        return False

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN MODE ENABLED: no database changes will be performed."
                )
            )

        self.nsc = NoSQLClient()

        processed_db = 0
        skipped_db = 0
        total_attachments = 0
        total_to_create = 0

        # Clear the attachment table only when not running in dry-run mode
        if dry_run:
            self.stdout.write(
                "[DRY-RUN] Attachment table cleanup skipped."
            )
        else:
            deleted_count, _ = Attachment.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted {deleted_count} existing Attachment records."
                )
            )

        facilitator_dbs = self.nsc.list_all_databases("facilitator")

        self.stdout.write(
            f"Found {len(facilitator_dbs)} facilitator databases."
        )

        for db_name in facilitator_dbs:

            try:
                self.stdout.write("")
                self.stdout.write(f"Processing database: {db_name}")

                # Skip development and training facilitators
                if not self.check_for_valid_facilitator(db_name):
                    skipped_db += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"[SKIPPED] {db_name} is a training/development facilitator."
                        )
                    )
                    continue

                db = self.nsc.get_db(db_name)

                task_documents = db.get_query_result({
                    "type": "task"
                })

                adm_id = None

                # Retrieve the administrative level from the first task
                for doc in task_documents:
                    adm_id = doc.get("administrative_level_id")
                    break

                if not adm_id:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[SKIPPED] No administrative_level_id found in {db_name}."
                        )
                    )
                    skipped_db += 1
                    continue

                extracted_attachments, skipped_local_files = \
                    get_attachments_from_database(task_documents)

                self.stdout.write(
                    f"  -> Found {len(extracted_attachments)} valid attachment(s)."
                )

                if skipped_local_files:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  -> Ignored {skipped_local_files} local file(s) "
                            f"(never uploaded from device)."
                        )
                    )
                attachment_count = len(extracted_attachments)

                self.stdout.write(
                    f"  -> Found {attachment_count} attachment(s)."
                )

                total_attachments += attachment_count

                try:
                    adm = AdministrativeLevel.objects.get(
                        no_sql_db_id=adm_id
                    )
                except AdministrativeLevel.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(
                            f"[ERROR] AdministrativeLevel not found for no_sql_db_id={adm_id}"
                        )
                    )
                    continue

                created_count = save_attachments_to_purs_test(
                    adm=adm,
                    extracted_attachments=extracted_attachments,
                    dry_run=dry_run,
                    stdout=self.stdout
                )

                total_to_create += created_count
                processed_db += 1

            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(
                        f"[ERROR] Failed processing {db_name}: {exc}"
                    )
                )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Databases processed : {processed_db}")
        self.stdout.write(f"Databases skipped   : {skipped_db}")
        self.stdout.write(f"Attachments found   : {total_attachments}")
        self.stdout.write(f"Attachments to save : {total_to_create}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN completed successfully. No data was modified."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Attachment extraction completed successfully."
                )
            )


def get_attachments_from_database(task_documents):
    """
    Extract attachments from task documents and enrich them
    with SQL Task information when available.
    """
    extracted_attachments = []
    skipped_local_files = 0

    for document in task_documents:

        for attachment in document.get("attachments", []):

            attachment_data = attachment.get("attachment")
            attachment_uri = (
                attachment_data.get("uri", "")
                if attachment_data else ""
            )
            # Skip local files that were never uploaded to MinIO.
            # These URIs point to the Android device filesystem and cannot be served by the application.
            if attachment_uri.startswith("file://"):
                skipped_local_files += 1
                continue

            try:
                task = Task.objects.get(
                    no_sql_db_id=document.get("_id")
                )
                task_name = task.name
                task_order = task.order

            except Task.DoesNotExist:
                task = None
                task_name = ""
                task_order = 0

            if attachment_uri:

                attachment_type = "document"

                lowered_uri = attachment_uri.lower()

                if (
                    lowered_uri.endswith(".jpg")
                    or lowered_uri.endswith(".jpeg")
                    or lowered_uri.endswith(".png")
                ):
                    attachment_type = "photo"

                extracted_attachments.append({
                    "type": attachment_type,
                    "url": attachment_uri,
                    "phase": document.get("phase_name", ""),
                    "activity": document.get("activity_name", ""),
                    "task": task,
                    "task_name": task_name,
                    "task_order": task_order
                })

    return extracted_attachments, skipped_local_files


def save_attachments_to_purs_test(
    adm,
    extracted_attachments,
    dry_run=False,
    stdout=None
):
    """
    Save extracted attachments to SQL database.
    When dry_run=True, only simulate the operation.
    """

    base_url = (
        "https://cdd.coso.gouv.bj/"
        "fr/facilitators/serve-minio-file/"
    )

    objects_to_create = []

    for attachment in extracted_attachments:

        url = attachment.get("url")

        objects_to_create.append(
            Attachment(
                adm=adm,
                type=attachment.get("type").capitalize(),
                url=f"{base_url}{url}",
                task=attachment.get("task"),
                name=attachment.get("task_name"),
                order=attachment.get("task_order")
            )
        )

    if dry_run:

        if stdout:
            stdout.write(
                f"  -> [DRY-RUN] {len(objects_to_create)} Attachment record(s) would be created."
            )

        return len(objects_to_create)

    Attachment.objects.bulk_create(objects_to_create)

    if stdout:
        stdout.write(
            f"  -> Created {len(objects_to_create)} Attachment record(s)."
        )

    return len(objects_to_create)