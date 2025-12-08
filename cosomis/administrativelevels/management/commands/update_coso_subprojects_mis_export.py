import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment
from cosomis.constants import STRUCTURE_COMPLETED_STATUS
from thefuzz import fuzz


class Command(BaseCommand):
    help = 'Reads an Excel file and processes it with a given project ID.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the Excel file.')
        parser.add_argument('project_id', type=int, help='The ID of the project.')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        project_id = kwargs['project_id']

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise CommandError(f'Project with ID {project_id} does not exist.')

        # Read the Excel file
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise CommandError(f'Error reading the Excel file: {e}')
        count = 0
        # Iterate over the dataframe and find the investments with ID in the Excel file
        for index, row in df.iterrows():
            investment_id = f'{project.name}.{row["ID"]}.{row["N"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
            try:
                investment = Investment.objects.get(imported_project_id=investment_id)
                try:
                    physical_execution_rate = float(row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"])
                    if pd.isna(physical_execution_rate):
                        physical_execution_rate = 0
                except:
                    physical_execution_rate = 0

                project_status = "P"
                if row["status"] == "Identifié":
                    project_status = "F"
                elif row["status"] == "En cours":
                    project_status = "P"
                elif pd.isna(row["status"]):
                    project_status = "F"
                elif row["status"] == "Arrêt":
                    project_status = "PA"
                elif row["status"] in STRUCTURE_COMPLETED_STATUS: #row["status"] == "Achevé" or row["status"] == "Réception provisoire" or row["status"] == "Réception technique":
                    project_status = "C"

                investment.physical_execution_rate = physical_execution_rate
                investment.project_status = project_status
                # longitude = row["Longitude (x)"],
                # latitude = row["Latitude (y)"],
                # if not pd.isna(longitude):
                #     investment.longitude = longitude
                # if not pd.isna(latitude):
                #     investment.latitude = latitude
                investment.save()
                print("Found", project_status, row["status"])
                count += 1
            except Investment.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Investment with ID {investment_id} does not exist.'))
                continue
            except Investment.MultipleObjectsReturned:
                self.stdout.write(self.style.ERROR(f'Multiple investments with ID {investment_id} exist.'))
                continue
        print(count)
        self.stdout.write(self.style.SUCCESS('Successfully proc') + 'essing the Excel file.')