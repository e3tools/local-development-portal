from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment, Attachment
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task
from investments.models import Sector


def update_or_create_document(document):
    # Extract the phase_id from the phase document
    object_id = document['_id']
    document_type = document['type']
    administrative_level_id = document['administrative_level_id']
    # Check if a document with the given phase_id exists in the 'purs_test' database
    if document_type == 'phase':
        existing_phase = Phase.objects.filter(
            no_sql_db_id=object_id,
            village=int(administrative_level_id)
        )
        if not existing_phase:
            try:
                Phase.objects.create(
                    no_sql_db_id=object_id,
                    village=AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id),
                    name=document['name'],
                    description=document['description'],
                    order=document['order'],
                )
            except Exception as e:
                print(e, "Error creating phase", document['name'], document['administrative_level_id'])
        else:
            try:
                existing_phase = existing_phase[0]
                existing_phase.name = document['name']
                existing_phase.description = document['description']
                existing_phase.order = document['order']
                existing_phase.save()
            except Exception as e:
                print(e, "Error updating phase", document['name'], document['administrative_level_id'])
    elif document_type == 'activity':
        existing_activity = Activity.objects.filter(
            no_sql_db_id=object_id,
            phase__village=int(administrative_level_id)
        )
        if not existing_activity:
            try:
                administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
                Activity.objects.create(
                    no_sql_db_id=object_id,
                    phase=Phase.objects.get(no_sql_db_id=document['phase_id'], village=administrative_level),
                    name=document['name'],
                    description=document['description'],
                    order=document['order'],
                )
            except Exception as e:
                print(e, "Error creating activity", document['name'], document['administrative_level_id'])
        else:
            existing_activity = existing_activity[0]
            existing_activity.name = document['name']
            existing_activity.description = document['description']
            existing_activity.order = document['order']
            existing_activity.save()

    elif document_type == 'task':
        existing_task = Task.objects.filter(
            no_sql_db_id=object_id,
            activity__phase__village=int(administrative_level_id)
        )
        if not existing_task:
            # try:
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            if document['completed']:
                status = 'completed'
            else:
                status = 'not started'
            existing_task = Task.objects.create(
                no_sql_db_id=object_id,
                activity=Activity.objects.get(no_sql_db_id=document['activity_id'], phase__village=administrative_level),
                name=document['name'],
                description=document['description'],
                order=document['order'],
                status=status,
                form_responses=document['form_response'],
                form=document['form'],
            )
            # except Exception as e:
            #     print(e, "Error creating task", document['name'], document['administrative_level_id'])
        else:
            if document['completed']:
                status = 'completed'
            else:
                status = 'not started'
            existing_task = existing_task.first()
            existing_task.name = document['name']
            existing_task.description = document['description']
            existing_task.order = document['order']
            existing_task.status = status
            existing_task.form_responses = document['form_response']
            existing_task.form = document['form']
            existing_task.save()



class Command(BaseCommand):
    help = 'Description of your command'

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
                    "type": "phase"
                })
                for document in db:
                    update_or_create_document(document)
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "activity"
                })
                for document in db:
                    update_or_create_document(document)
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "task"
                })
                for document in db:
                    update_or_create_document(document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
