from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel
from investments.models import Category, Sector



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
                    "name": "Identification et établissement de la liste des besoins prioritaires pour la composante 1.1  par groupe"
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
        try:
            if priorities_document.get('form_response') and 'agriculteursEtEleveurs' in priorities_document['form_response'][0]:
                for idx, priority in enumerate(
                        priorities_document['form_response'][0]['agriculteursEtEleveurs']['besoinsPrioritairesDuGroupe']):
                        investment = Investment.objects.filter(
                            administrative_level=administrative_level,
                            title=priority['besoinSelectionne']
                        )
                        if investment:
                            investment = investment.first()
                            investment.endorsed_by_agriculturist = True
                            investment.save()
        except:
            pass
        try:
            if priorities_document.get('form_response') and 'groupeDesFemmes' in priorities_document['form_response'][1]:
                for idx, priority in enumerate(
                        priorities_document['form_response'][1]['groupeDesFemmes']['besoinsPrioritairesDuGroupe']):
                        investment = Investment.objects.filter(
                            administrative_level=administrative_level,
                            title=priority['besoinSelectionne']
                        )
                        if investment:
                            investment = investment.first()
                            investment.endorsed_by_women = True
                            investment.save()
        except:
            pass
        try:
            if priorities_document.get('form_response') and 'groupeDesJeunes' in priorities_document['form_response'][2]:
                for idx, priority in enumerate(
                        priorities_document['form_response'][2]['groupeDesJeunes']['besoinsPrioritairesDuGroupe']):
                        investment = Investment.objects.filter(
                            administrative_level=administrative_level,
                            title=priority['besoinSelectionne']
                        )
                        if investment:
                            investment = investment.first()
                            investment.endorsed_by_youth = True
                            investment.save()
        except:
            pass
        try:
            if priorities_document.get('form_response') and 'groupeEthniqueMinoritaires' in priorities_document['form_response'][3]:
                for idx, priority in enumerate(
                        priorities_document['form_response'][3]['groupeEthniqueMinoritaires']['besoinsPrioritairesDuGroupe']):
                        investment = Investment.objects.filter(
                            administrative_level=administrative_level,
                            title=priority['besoinSelectionne']
                        )
                        if investment:
                            investment = investment.first()
                            investment.endorsed_by_pastoralist = True
                            investment.save()
        except:
            pass
