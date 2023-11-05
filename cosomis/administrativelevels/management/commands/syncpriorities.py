from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import Category, AdministrativeLevel

class Command(BaseCommand):
    help = 'Description of your command'

    def add_arguments(self, parser):
        # You can add command-line arguments here, if needed
        pass

    def handle(self, *args, **options):
        # Your command logic here
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            db = self.nsc.get_db(db_name).get_query_result({
                "type": "task",
                "phase_name": "PLANIFICATION",
                "name": "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage"
            })
            for document in db:
                update_or_create_priorities_document(document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))


def update_or_create_priorities_document(priorities_document):
    # Extract the administrative_level_id from the priorities document
    adm_id = priorities_document['administrative_level_id']

    # Check if a document with the given adm_id exists in the 'purs_test' database
    selector = {
        "adm_id": adm_id,
        "type": "administrative_level"
    }
    administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    existing_doc = Investment.objects.filter(no_sql_id=adm_id)
    # TODO Complete Sector Allocation
    # Extract priorities from the priorities document
    if 'form_response' in priorities_document:
        if priorities_document.get('form_response') and 'sousComposante11' in priorities_document['form_response'][0]:
            for idx, priority in enumerate(priorities_document['form_response'][0]['sousComposante11']['prioritesDuVillage']):
                print(idx)
                Investment.objects.create(
                    ranking=idx + 1,
                    title=priority["priorite"],
                    estimated_cost=priority.get("coutEstime"),
                    sector=Category.objects.get(id=1),
                    delays_consumed=0,
                    duration=0,
                    financial_implementation_rate=0,
                    physical_execution_rate=0,
                    administrative_level=administrative_level,
                    #beneficiaries= priority.get("nombreEstimeDeBeneficiaires"),
                )

            # extracted_priorities = [
            #     {
            #         "ranking": idx + 1,
            #         "name": priority["priorite"],
            #         "votes_young": None,  # Placeholder as it's not clear where to get this from
            #         "votes_woman": None,  # Placeholder
            #         "votes_me": None,  # Placeholder
            #         "votes_ae": None,  # Placeholder
            #         "beneficiaries": priority.get("nombreEstimeDeBeneficiaires"),
            #         "estimated_cost": priority.get("coutEstime"),
            #         "financed_by": None,  # Placeholder
            #         "contrubution_to_climate": True if priority.get("contributionClimatique") else False
            #     } for idx, priority in
            #     enumerate(priorities_document['form_response'][0]['sousComposante11']['prioritesDuVillage'])
            # ]
    # If the document exists, update it

    # Otherwise, create a new one
    print("adm_id: ", adm_id)
    time.sleep(1)
