from django.core.management.base import BaseCommand
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment

class Command(BaseCommand):
    help = 'Uploads the facilitator of an administrative level'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the Excel file.')
        parser.add_argument('project_id', type=int, help='The ID of the project.')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise CommandError(f'Error reading the Excel file: {e}')

        count = 0
        for index, row in df.iterrows():
            admin_level_id = row["ID"]
            try:
                update_adm(admin_level_id, row)
                count += 1
            except AdministrativeLevel.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'AdministrativeLevel with ID {admin_level_id} does not exist.'))
                continue
            except AdministrativeLevel.MultipleObjectsReturned:
                self.stdout.write(self.style.ERROR(f'Multiple administrative levels with ID {admin_level_id} exist.'))
                continue
        print(count)
        self.stdout.write(self.style.SUCCESS('Successfully proc') + 'essing the Excel file.')


def update_adm(adm_id, row):
    adm_level = AdministrativeLevel.objects.get(no_sql_db_id=adm_id)
    adm_level.facilitator = row["facilitator"]
    adm_level.save()


