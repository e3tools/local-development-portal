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
        db = self.nsc.get_db('administrative_levels')
        selector = {
            "type": "administrative_level",
            "administrative_level": "Village"
        }
        # docs = Result(db.all_docs, include_docs=True, selector=selector).all()
        docs = db.get_query_result(selector)
        for document in docs:
            update_document(self.nsc, document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

def update_document(client, administrative_level):

    # Access the 'purs_test' database
    db = client.get_db('purs_test')

    # Extract the administrative_level_id from the priorities document
    adm_id = administrative_level['administrative_id']

    # Check if a document with the given adm_id exists in the 'purs_test' database
    selector = {
        "adm_id": adm_id,
        "type": "administrative_level"
    }

    docs = db.get_query_result(selector)

    adm_name = administrative_level['name']
    adm_parent = administrative_level['parent_id']

    existing_doc = False
    for doc in docs:
        existing_doc = doc
        break
    # If the document exists, update it
    if existing_doc:
        with Document(db, existing_doc['_id']) as document:
            # The document is fetched from the remote database
            # Changes are made locally
            # update the document with "total_population": 0,
            try:
                document['name'] = adm_name
                document['parent_id'] = adm_parent
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
            'parent_id': adm_parent
        }
        db.create_document(new_doc)
