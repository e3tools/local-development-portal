from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task
from investments.models import Category, Sector


def update_or_create_phase(phase_document):
    # Extract the phase_id from the phase document
    phase_id = phase_document['sql_id']

    # Check if a document with the given phase_id exists in the 'purs_test' database
    print("Phase Document", phase_id)
    phase = Phase.objects.get(no_sql_db_id=phase_id)
    print("Phase", phase)


class Command(BaseCommand):
    help = 'Description of your command'

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    print("Facilitator is valid", document)
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        # Your command logic here
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "phase"
                })
                for document in db:
                    update_or_create_phase(document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
