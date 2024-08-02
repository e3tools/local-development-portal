import json
from django.core.management.base import BaseCommand, CommandError
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel
from investments.models import Category, Sector


class Command(BaseCommand):
    help = 'Export all of the tasks data into a json file'

    total_priorities = 0
    total_villages = 0
    total_not_collected_villages = 0
    not_collected_villages_ids = []
    data_collected = {
        "exported_date": "02-08-2024",
        "data": []
    }

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
                db = self.nsc.get_db(db_name).get_query_result({
                    "type": "task"
                })
                for document in db:
                    self.format_task(document)
        # Save data_collected to a JSON file
        with open('./data_collected.json', 'w') as outfile:
            json.dump(self.data_collected, outfile, indent=4)

        self.stdout.write(self.style.SUCCESS('Successfully exported all of the tasks data!'))

    def format_task(self, document):
        adm_id = document['administrative_level_id']
        self.total_villages += 1
        administrative_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
        administrative_level_data = {}
        levels = []
        current_level = administrative_level

        while current_level is not None:
            levels.append((current_level.id, current_level.name))
            current_level = current_level.parent

        levels.reverse()

        for level_counter, (level_id, level_name) in enumerate(levels):
            administrative_level_data[f'adm_{level_counter}_id'] = level_id
            administrative_level_data[f'adm_{level_counter}_name'] = level_name

        extracted_data = {
            "administrative_level_data": administrative_level_data,
            "phase_name": document['phase_name'],
            "activity_name": document['activity_name'],
            "name": document['name'],
            "description": document['description'],
            "completed": document['completed'],
            "form_response": document['form_response'],
        }

        # Append extracted data to data_collected
        self.data_collected['data'].append(extracted_data)
