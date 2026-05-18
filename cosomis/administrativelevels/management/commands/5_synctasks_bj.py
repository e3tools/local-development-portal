from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment, Attachment
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task
from investments.models import Sector


def update_or_create_phase(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            phase, created = Phase.objects.get_or_create(
                no_sql_db_id=object_id,
                village=administrative_level,
                defaults={
                    'name': document['name'],
                    'description': document['description'],
                    'order': document['order'],
                }
            )
            if not created:
                phase.name = document['name']
                phase.description = document['description']
                phase.order = document['order']
                phase.save()
    except Exception as e:
        print(e, "Error processing phase:", document['name'], document['administrative_level_id'])


def update_or_create_activity(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            phase = Phase.objects.get(no_sql_db_id=document['phase_id'], village=administrative_level)
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
        print(e, "Error processing activity:", document['name'], document['administrative_level_id'])


def update_or_create_task(document):
    object_id = document['_id']
    administrative_level_id = document['administrative_level_id']
    try:
        with transaction.atomic():
            administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=administrative_level_id)
            activity = Activity.objects.get(no_sql_db_id=document['activity_id'], phase__village=administrative_level)
            status = 'completed' if document['completed'] else 'not started'
            task, created = Task.objects.get_or_create(
                no_sql_db_id=object_id,
                activity=activity,
                defaults={
                    'name': document['name'],
                    'description': document['description'],
                    'order': document['order'],
                    'status': status,
                    'form_responses': document.get('form_response', {}),
                    'form': document.get('form', ''),
                }
            )
            if not created:
                task.name = document['name']
                task.description = document['description']
                task.order = document['order']
                task.status = status
                task.form_responses = document.get('form_response', {})
                task.form = document.get('form', '')
                task.save()
    except Exception as e:
        print(e, "Error processing task:", document['name'], document['administrative_level_id'])


class Command(BaseCommand):
    help = 'Description of your command'

    def check_for_valid_facilitator(self, facilitator):
        db = self.nsc.get_db(facilitator).get_query_result({
            "type": "facilitator"
        })
        for document in db:
            try:
                dev_mode = document.get('develop_mode', False)
                train_mode = document.get('training_mode', False)
                if not dev_mode and not train_mode:
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

                # Then create all activities
                db = self.nsc.get_db(db_name).get_query_result({"type": "activity"})
                for document in db:
                    update_or_create_activity(document)

                # Finally, create all tasks
                db = self.nsc.get_db(db_name).get_query_result({"type": "task"})
                for document in db:
                    update_or_create_task(document)

        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
