import json
from django.core.management.base import BaseCommand, CommandError
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel, Task, Activity, Phase


def parse_fields(fields, field_types, response):
    matched_responses = []

    for key, field_info in fields.items():
        if "fields" in field_info:  # Nested fields
            nested_fields = field_info["fields"]
            nested_field_types = field_types[key]["properties"] if key in field_types and "properties" in field_types[key] else {}
            nested_response = response[key] if key in response else {}
            nested_responses = parse_fields(nested_fields, nested_field_types, nested_response)
            for nested_response in nested_responses:
                matched_responses.append(nested_response)
        elif key in response:  # Base case
            response_value = response[key]
            field_type = field_types[key]["type"] if key in field_types else "unknown"
            matched_responses.append({
                "label": field_info["label"],
                "response": response_value,
                "type": field_type
            })

    return matched_responses

def match_form_labels_with_responses(form, form_responses):
    all_matched_responses = []

    for form_section, response_section in zip(form, form_responses):
        fields = form_section["options"]["fields"]
        field_types = form_section["page"]["properties"]
        response = response_section

        matched_responses = parse_fields(fields, field_types, response)
        all_matched_responses.extend(matched_responses)

    return json.dumps(all_matched_responses, ensure_ascii=False)

def update_task_responses(document):
    try:
        parsed_result = match_form_labels_with_responses(
            document['form'], document['form_response']
        )
        task = Task.objects.get(no_sql_db_id=document['_id'])
        task.form_responses = parsed_result
        task.save()
    except Exception as e:
        print(e, "Error updating task", document['_id'])


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
                    "type": "task",
                    "completed": True
                })
                for document in db:
                    update_task_responses(document)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))



