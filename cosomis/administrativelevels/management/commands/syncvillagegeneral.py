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
        db = client.get_db('administrative_levels')
        selector = {
            "type": "administrative_level"
        }
        # docs = Result(db.all_docs, include_docs=True, selector=selector).all()
        docs = db.get_query_result(selector)
        for document in docs:
            update_document(document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))

def update_document(administrative_level):
    print(administrative_level)
    return True
