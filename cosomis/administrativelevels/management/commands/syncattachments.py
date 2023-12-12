from django.core.management.base import BaseCommand, CommandError
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from administrativelevels.models import AdministrativeLevel
from investments.models import Attachment


class Command(BaseCommand):
    help = 'Extract attachments from task documents and save to purs_test database'

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            print("Facilitator", document)
            try:
                if not document['develop_mode'] and not document["training_mode"]:
                    print("Facilitator is valid", document)
                    return True
            except:
                return False
        return False

    def handle(self, *args, **options):
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                extracted_attachments = []
                db = self.nsc.get_db(db_name)
                task_documents = db.get_query_result({
                    "type": "task"
                })
                adm_id = None
                for doc in task_documents:
                    adm_id = doc['administrative_level_id']
                    break
                extracted_attachments = get_attachments_from_database(task_documents)
                if adm_id:
                    adm = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
                    save_attachments_to_purs_test(adm, extracted_attachments)
        self.stdout.write(self.style.SUCCESS('Successfully extracted attachments!'))


def get_attachments_from_database(task_documents):
    extracted_attachments = []
    for document in task_documents:
        for attachment in document.get('attachments', []):
            attachment_data = attachment.get('attachment')
            attachment_uri = attachment_data.get('uri', "") if attachment_data else ""
            if attachment_uri:
                extracted_attachments.append({
                    "type": "photo" if "photo" in attachment['name'].lower() else "document",
                    "url": attachment_uri,
                    "phase": document.get('phase_name', ""),
                    "activity": document.get('activity_name', ""),
                    "task": document.get('name', "")
                })
    return extracted_attachments

def save_attachments_to_purs_test(adm, extracted_attachments):
    # Access the 'purs_test' database

    # Create a new document with the extracted attachments
    for attachment in extracted_attachments:
        print(attachment)
        Attachment.objects.create(
            adm=adm,
            type=attachment.get('type').capitalize(),
            url=attachment.get('url')
        )
