from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from administrativelevels.models import AdministrativeLevel


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
            "administrative_level": "Country"
        }
        docs = db.get_query_result(selector)
        for document in docs:
            create_or_update_adm(document)
            recursive_administrative_level(document, db)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))


def recursive_administrative_level(administrative_level, database):
    print(
        administrative_level['name'],
        administrative_level['administrative_level'],
        administrative_level['administrative_id']
    )
    selector = {
        "type": "administrative_level",
        "parent_id": administrative_level['administrative_id']
    }
    docs = database.get_query_result(selector)
    for document in docs:
        create_or_update_adm(document)
        recursive_administrative_level(document, database)


def create_or_update_adm(administrative_level_data):
    # Extract the administrative_level_id and other fields from the data
    adm_id = administrative_level_data.get('administrative_id')
    adm_name = administrative_level_data.get('name')
    adm_parent_id = administrative_level_data.get('parent_id')
    adm_type = administrative_level_data.get('administrative_level')
    # Other fields can be added as needed

    # Check if an AdministrativeLevel with the given adm_id exists
    try:
        adm_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
        # If the record exists, update it
        adm_level.name = adm_name
        adm_level.type = adm_type
        if adm_parent_id:
            # Set the parent if a parent_id is provided, otherwise leave it unchanged
            parent = AdministrativeLevel.objects.get(no_sql_db_id=adm_parent_id)
            adm_level.parent = parent
        # You can add more fields to update as necessary
        adm_level.save()
    except AdministrativeLevel.DoesNotExist:
        # If the record does not exist, create a new one
        parent = None
        if adm_parent_id:
            # Set the parent if a parent_id is provided, otherwise leave it unchanged
            parent = AdministrativeLevel.objects.get(no_sql_db_id=adm_parent_id)
        adm_level = AdministrativeLevel(
            no_sql_db_id=adm_id,
            name=adm_name,
            # Assuming the 'parent' field is a ForeignKey to another AdministrativeLevel
            parent=parent,
            type=adm_type,
            # Set other fields with defaults or extract from administrative_level_data
        )
        adm_level.save()

    # The record is now saved or updated in the Django model
