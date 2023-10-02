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
                "phase_name": "PLANIFICATION",
                "name": "Soutenir la communauté dans la sélection des priorités par sous-composante (1.1, 1.2 et 1.3) à soumettre à la discussion du CCD lors de la réunion cantonale d'arbitrage"
            })
            for document in db:
                update_or_create_priorities_document(self.nsc, document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))


def update_or_create_priorities_document(client, priorities_document):
    # Access the 'purs_test' database
    db = client.get_db('purs_test')

    # Extract the administrative_level_id from the priorities document
    adm_id = priorities_document['administrative_level_id']

    # Check if a document with the given adm_id exists in the 'purs_test' database
    selector = {
        "adm_id": adm_id,
        "type": "administrative_level"
    }
    # docs = Result(db.all_docs, include_docs=True, selector=selector).all()
    docs = db.get_query_result(selector)
    existing_doc = False
    for doc in docs:
        existing_doc = doc
        break
    # Extract priorities from the priorities document
    if 'form_response' in priorities_document:
        if priorities_document.get('form_response') and 'sousComposante11' in priorities_document['form_response'][0]:
            extracted_priorities = [
                {
                    "ranking": idx + 1,
                    "name": priority["priorite"],
                    "votes_young": None,  # Placeholder as it's not clear where to get this from
                    "votes_woman": None,  # Placeholder
                    "votes_me": None,  # Placeholder
                    "votes_ae": None,  # Placeholder
                    "beneficiaries": priority.get("nombreEstimeDeBeneficiaires"),
                    "estimated_cost": priority.get("coutEstime"),
                    "financed_by": None,  # Placeholder
                    "contrubution_to_climate": True if priority.get("contributionClimatique") else False
                } for idx, priority in
                enumerate(priorities_document['form_response'][0]['sousComposante11']['prioritesDuVillage'])
            ]
        else:
            extracted_priorities = []
    else:
        extracted_priorities = []

    # If the document exists, update it
    if existing_doc:
        with Document(db, existing_doc['_id']) as document:
            # The document is fetched from the remote database
            # Changes are made locally
            try:
                document['priorities'] = extracted_priorities
                document['last_updated'] = priorities_document['last_updated']
            except:
                pass
    # Otherwise, create a new one
    else:
        new_doc = {
            # "_id": db.create_document()['id'],  # Generating a new CouchDB ID
            "adm_id": adm_id,
            "type": "administrative_level",
            "priorities": extracted_priorities,
            "last_updated": priorities_document['last_updated']
        }
        db.create_document(new_doc)