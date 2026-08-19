from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import time
from django.db.models import Q
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment, Attachment
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project
from investments.models import Sector


def update_or_create_phase(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    # Comme les documents "task" utilisés par 2_syncpriorities.py, les documents
    # "phase" portent project_name : on le résout en Project pour pouvoir
    # regrouper le cycle de planification par projet (COSO/FA-COSO/PURS/...).
    project = None
    project_name = document.get('project_name')
    if project_name:
        project = Project.objects.filter(name__iexact=project_name).first()
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            phase, created = Phase.objects.get_or_create(
                no_sql_db_id=object_id,
                village=administrative_level,
                project=project,
                defaults={
                    'name': document['name'],
                    'description': document['description'],
                    'order': document['order']
                }
            )
            if not created:
                phase.name = document['name']
                phase.description = document['description']
                phase.order = document['order']
                if project:
                    phase.project = project
                phase.save()
    except Exception as e:
        print(e, "Error processing phase:", document['name'], document['administrative_level_id'], document['project_name'])


def update_or_create_activity(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            phase = Phase.objects.get(no_sql_db_id=document['phase_id'], village=administrative_level, project__name__iexact=document['project_name'])
            activity, created = Activity.objects.get_or_create(
                no_sql_db_id=object_id,
                phase=phase,
                defaults={
                    'name': document['name'],
                    'description': document['description'],
                    'order': document['order'],
                }
            )
            if not created:
                activity.name = document['name']
                activity.description = document['description']
                activity.order = document['order']
                activity.save()
    except Exception as e:
        print(e, "Error processing activity:", document['name'], document['administrative_level_id'], document['project_name'])


def update_or_create_task(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            activity = Activity.objects.filter(phase__village=administrative_level, phase__project__name__iexact=document['project_name']).get(Q(no_sql_db_id=document['activity_id']) | Q(name__iexact=document['activity_name']))
            form_response = document.get('form_response', {})
            status = Task.COMPLETED if document['completed'] else (Task.IN_PROGRESS if form_response else Task.NOT_STARTED) #(('invalidated' if document['validated'] else 'invalidated') if 'validated' in document else 'completed') if document['completed'] else ('in progress' if form_response else 'not started')
            task, created = Task.objects.get_or_create(
                no_sql_db_id=object_id,
                activity=activity,
                defaults={
                    'name': document['name'],
                    'description': document['description'],
                    'order': document['order'],
                    'status': status,
                    'form_responses': form_response,
                    'form': document.get('form', ''),
                }
            )
            if not created:
                task.name = document['name']
                task.description = document['description']
                task.order = document['order']
                task.status = status
                task.form_responses = form_response
                task.form = document.get('form', '')
                task.save()
    except Exception as e:
        print(e, "Error processing task:", document['name'], document['administrative_level_id'], document['project_name'])


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
        self.nsc = NoSQLClient()
        facilitator_dbs = self.nsc.list_all_databases('facilitator')
        for db_name in facilitator_dbs:
            if self.check_for_valid_facilitator(db_name):
                # Ensure all phases are created first
                db = self.nsc.get_db(db_name).get_query_result({"type": "phase"})
                for document in db:
                    update_or_create_phase(document)
                time.sleep(1)

                # Then create all activities
                db = self.nsc.get_db(db_name).get_query_result({"type": "activity"})
                for document in db:
                    update_or_create_activity(document)
                time.sleep(1)

                # Finally, create all tasks
                db = self.nsc.get_db(db_name).get_query_result({"type": "task"})
                for document in db:
                    update_or_create_task(document)
                time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))