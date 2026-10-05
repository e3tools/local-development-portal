from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Sector
from administrativelevels.management.commands._couch_sync import add_validated_argument, with_validated

counter = 0

class Command(BaseCommand):
    help = 'Check which villages do not have the three required investments'

    def add_arguments(self, parser):
        add_validated_argument(parser)

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        # Initialize NoSQL Client
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')

        # Iterate over each facilitator database
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                db = self.nsc.get_db(db_name).get_query_result(with_validated({
                    "type": "task",
                    "phase_name": "PLANIFICATION",
                    "name": "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage"
                }, options['validated']))

                # Check for villages missing investments
                for document in db:
                    self.check_village_investments(document)

        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

    def check_village_investments(self, priorities_document):
        # Extract the administrative_level_id from the priorities document
        adm_id = priorities_document['administrative_level_id']
        try:
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)

            # Retrieve the required investments for this village
            village_investments = Investment.objects.filter(administrative_level=administrative_level)

            # Define required investment titles (example: can be customized)
            required_investments = ["Investment 1", "Investment 2", "Investment 3"]
            existing_investments = village_investments.values_list('title', flat=True)

            # Identify missing investments
            missing_investments = [investment.title for investment in existing_investments]
            if existing_investments.count() < 3:
                print(
                    f"Village {administrative_level.name} with if {administrative_level.id} is missing the following amount of priorities: {3 - existing_investments.count()}")
            else:
                pass

        except AdministrativeLevel.DoesNotExist:
            print(f"Administrative level with ID {adm_id} not found.")