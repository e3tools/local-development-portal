from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Category
from investments.models import Sector



class Command(BaseCommand):

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
        # Your command logic here
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
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

    administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    # TODO Complete Sector Allocation
    # Extract priorities from the priorities document
    if 'form_response' in priorities_document:
        if priorities_document.get('form_response') and 'sousComposante11' in priorities_document['form_response'][0]:
            for idx, priority in enumerate(
                    priorities_document['form_response'][0]['sousComposante11']['prioritesDuVillage']):
                try:
                    investment = Investment.objects.filter(
                        administrative_level=administrative_level,
                        title=priority['priorite']
                    )
                    if investment:
                        investment = investment.first()
                        investment.description = priority["siAutreVeuillezDecrire"]
                        investment.save()
                except Exception as e:
                    print(e, "Error creating investment", priority["priorite"], administrative_level)
    # Otherwise, create a new one
    time.sleep(0.3)