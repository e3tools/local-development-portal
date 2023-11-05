from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from administrativelevels.models import AdministrativeLevel

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
                "phase_name": "VISITES PREALABLES",
                "name": "Etablissement du profil du village",
            })
            for document in db:
                update_or_create_adm_document(self.nsc, document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

def update_or_create_adm_document(client, population_document):

    # Access the 'purs_test' database

    # Extract the administrative_level_id from the priorities document
    adm_id = population_document['administrative_level_id']

    # Check if a document with the given adm_id exists in the 'purs_test' database
    selector = {
        "adm_id": adm_id,
        "type": "administrative_level"
    }
    # docs = Result(db.all_docs, include_docs=True, selector=selector).all()

    adm_object = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)

    extracted_population_data = None

    # Extract priorities from the priorities document
    if 'form_response' in population_document:
        if population_document.get('form_response'):
            extracted_population_data = extract_population_data(population_document['form_response'])

    if not extracted_population_data:
        return

    # If the document exists, update it
    if adm_object:
        adm_object.total_population = extracted_population_data['total_population']
        adm_object.population_men = extracted_population_data['population_men']
        adm_object.population_women = extracted_population_data['population_women']
        adm_object.population_young = extracted_population_data['population_young']
        adm_object.population_elder = extracted_population_data['population_elder']
        adm_object.population_handicap = extracted_population_data['population_handicap']
        adm_object.population_agriculture = extracted_population_data['population_agriculture']
        adm_object.population_breeders = extracted_population_data['population_breeders']
        adm_object.population_minorities = extracted_population_data['population_minorities']
        adm_object.save()


def extract_population_data(form_response):
    extracted_population_data = {
        "total_population": 0,
        "population_men": 0,
        "population_women": 0,
        "population_young": 0,
        "population_elder": 0,
        "population_handicap": 0,
        "population_agriculture": 0,
        "population_breeders": 0,
        "population_minorities": 0
    }

    for entry in form_response:
        if "population" in entry:
            extracted_population_data["total_population"] = entry["population"].get("populationTotaleDuVillage", 0)
            extracted_population_data["population_men"] = entry["population"].get("populationNombreDeHommes", 0)
            extracted_population_data["population_women"] = entry["population"].get("populationNombreDeFemmes", 0)

        elif "personnesVulnerables" in entry and entry["personnesVulnerables"] is not None:
            persons_vulnerable = entry["personnesVulnerables"]

            if "populationEnfants" in persons_vulnerable and persons_vulnerable["populationEnfants"] is not None:
                extracted_population_data["population_young"] = persons_vulnerable["populationEnfants"].get(
                    "enfantsTotal", 0)

            if "populationPersonnesAgees" in persons_vulnerable and persons_vulnerable[
                "populationPersonnesAgees"] is not None:
                extracted_population_data["population_elder"] = persons_vulnerable["populationPersonnesAgees"].get(
                    "populationPersonnesAgeesTotal", 0)

            if "populationPersonnesHandicape" in persons_vulnerable and persons_vulnerable[
                "populationPersonnesHandicape"] is not None:
                extracted_population_data["population_handicap"] = persons_vulnerable[
                    "populationPersonnesHandicape"].get("populationPersonnesHandicapeTotal", 0)

    print('here is the result:', extracted_population_data)
    return extracted_population_data
