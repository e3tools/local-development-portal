from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document

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
    db = client.get_db('purs_test')
    db_administrative_level = client.get_db('administrative_levels')

    # Extract the administrative_level_id from the priorities document
    adm_id = population_document['administrative_level_id']

    # Check if a document with the given adm_id exists in the 'purs_test' database
    selector = {
        "adm_id": adm_id,
        "type": "administrative_level"
    }
    # docs = Result(db.all_docs, include_docs=True, selector=selector).all()
    docs = db.get_query_result(selector)

    adm_object = db_administrative_level.get_query_result({
        "administrative_id": adm_id,
        "type": "administrative_level"
    })

    existing_adm = False
    adm_name = None
    for adm in adm_object:
        adm_name = adm['name']
        break

    existing_doc = False
    for doc in docs:
        existing_doc = doc
        break

    extracted_population_data = None

    # Extract priorities from the priorities document
    if 'form_response' in population_document:
        if population_document.get('form_response'):
            extracted_population_data = extract_population_data(population_document['form_response'])

    if not extracted_population_data:
        return

    # If the document exists, update it
    if existing_doc:
        with Document(db, existing_doc['_id']) as document:
            # The document is fetched from the remote database
            # Changes are made locally
            # update the document with "total_population": 0,
            try:
                document['name'] = adm_name
                document['total_population'] = extracted_population_data['total_population']
                document['population_men'] = extracted_population_data['population_men']
                document['population_women'] = extracted_population_data['population_women']
                document['population_young'] = extracted_population_data['population_young']
                document['population_elder'] = extracted_population_data['population_elder']
                document['population_handicap'] = extracted_population_data['population_handicap']
                document['population_agriculture'] = extracted_population_data['population_agriculture']
                document['population_breeders'] = extracted_population_data['population_breeders']
                document['population_minorities'] = extracted_population_data['population_minorities']
            except:
                pass
    # Otherwise, create a new one
    else:
        new_doc = {
            # "_id": db.create_document()['id'],  # Generating a new CouchDB ID
            "adm_id": adm_id,
            "type": "administrative_level",
            "level": "village",
            "name": adm_name,
            'total_population': extracted_population_data['total_population'],
            'population_men': extracted_population_data['population_men'],
            'population_women': extracted_population_data['population_women'],
            'population_young': extracted_population_data['population_young'],
            'population_elder': extracted_population_data['population_elder'],
            'population_handicap': extracted_population_data['population_handicap'],
            'population_agriculture': extracted_population_data['population_agriculture'],
            'population_breeders': extracted_population_data['population_breeders'],
            'population_minorities': extracted_population_data['population_minorities']
        }
        db.create_document(new_doc)


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
