from django.core.management.base import BaseCommand
from django.db import transaction
from no_sql_client import NoSQLClient

from ._couch_sync import (
    SyncReport, add_validated_argument, adm_ids_by_couch_id, fetch_documents, sync_task_attachments,
    valid_facilitator_dbs,
)


class Command(BaseCommand):
    help = 'Create the attachments referenced by the task documents of the facilitator CouchDB databases'

    def add_arguments(self, parser):
        add_validated_argument(parser)

    def handle(self, *args, **options):
        nsc = NoSQLClient()
        adm_ids = adm_ids_by_couch_id()
        total = SyncReport()
        for db_name in valid_facilitator_dbs(nsc):
            # Only the fields used here: task documents also carry their forms.
            documents = fetch_documents(
                nsc, db_name, ('task',), fields=['_id', 'name', 'administrative_level_id', 'attachments'],
                validated=options['validated'],
            )
            with transaction.atomic():
                report = sync_task_attachments(documents['task'], adm_ids)
            for error in report.errors:
                self.stderr.write('%s: %s' % (db_name, error))
            total.merge(report)
        self.stdout.write(self.style.SUCCESS('Attachments synced: %s, %s errors' % (
            total.summary(), len(total.errors)
        )))
