from django.core.management.base import BaseCommand
from django.db import transaction
from no_sql_client import NoSQLClient

from ._couch_sync import (
    SyncReport, add_validated_argument, adm_ids_by_couch_id, fetch_documents, project_ids_by_name,
    sync_planning_cycle, valid_facilitator_dbs,
)


class Command(BaseCommand):
    help = 'Sync the planning cycle (phases, activities, tasks) from the facilitator CouchDB databases'

    def add_arguments(self, parser):
        add_validated_argument(parser)

    def handle(self, *args, **options):
        nsc = NoSQLClient()
        adm_ids = adm_ids_by_couch_id()
        project_ids = project_ids_by_name()
        total = SyncReport()
        for db_name in valid_facilitator_dbs(nsc):
            documents = fetch_documents(
                nsc, db_name, ('phase', 'activity', 'task'), validated=options['validated']
            )
            with transaction.atomic():
                report = sync_planning_cycle(
                    documents['phase'], documents['activity'], documents['task'], adm_ids, project_ids,
                    validated=options['validated'],
                )
            for error in report.errors:
                self.stderr.write('%s: %s' % (db_name, error))
            total.merge(report)
        self.stdout.write(self.style.SUCCESS('Planning cycle synced: %s, %s errors' % (
            total.summary(), len(total.errors)
        )))
