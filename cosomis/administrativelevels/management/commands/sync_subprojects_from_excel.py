import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment
from cosomis.constants import STRUCTURE_COMPLETED_STATUS
# from thefuzz import fuzz
from fuzzywuzzy import fuzz
from administrativelevels.utils.functions import normalize_text
import math


def safe_float(value):
    try:
        if value in ["NaN", "nan", "", None]:
            return 0
        v = float(value)
        if math.isnan(v):
            return 0
        return v
    except:
        return 0

def safe_value(value):
    try:
        if not value or (value and str(value).lower() in ["nan", "", "none"]):
            return None
        return value
    except:
        return None
    

class Command(BaseCommand):
    help = 'Reads an Excel file and processes it with a given project ID.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the Excel file.')
        parser.add_argument('project_id', type=int, help='The ID of the project.')

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        project_id = kwargs['project_id']
        project = Project.objects.get(pk=project_id)
        similarity_threshold = 100  # For matching the investment title
        count = 0
        not_matched = 0
        # Validate that the project exists
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            raise CommandError(f'Project with ID {project_id} does not exist.')

        # Read the Excel file
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            raise CommandError(f'Error reading the Excel file: {e}')

        # Process the DataFrame (example of processing)
        for index, row in df.iterrows():
            village = AdministrativeLevel.objects.filter(
                name=row["village"],
                parent__name=row["parent_adm"],
                parent__parent__name=row["parent_parent_adm"],
            )
            if village.count() == 1:
                imported_project_id = f'{project.name}.{row["ID"]}.{row["N"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                investments = Investment.objects.filter(
                    administrative_level=village.first(),
                    came_from__id=project_id,
                    imported_project_id=imported_project_id
                )
                if investments.exists():
                    matched_investments = list(investments)
                else:
                    # Iterate over the Investment objects and calculate the similarity
                    investments = Investment.objects.filter(
                        administrative_level=village.first(),
                        came_from__id=project_id
                    )
                    # Filter by similarity manually
                    matched_investments = [
                        investment for investment in investments
                        # if fuzz.ratio(investment.title, (row["CDD Option"] if safe_value(row["CDD Option"]) else row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])) >= similarity_threshold and (
                        #     (investment.funded_by and investment.funded_by_id==project_id) or not investment.funded_by
                        # )
                        if fuzz.token_set_ratio(normalize_text(investment.title), normalize_text(row["CDD Option"] if safe_value(row["CDD Option"]) else row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])) >= similarity_threshold and (
                            (investment.funded_by and investment.funded_by_id==project_id) or not investment.funded_by
                        )
                    ]

                # Sort by similarity if you want the best match first
                matched_investments.sort(key=lambda inv: fuzz.token_set_ratio(normalize_text(inv.title), normalize_text(row["CDD Option"] if safe_value(row["CDD Option"]) else row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])),
                                        reverse=True)
                if matched_investments:
                    best_match = matched_investments[0]  # The best match based on similarity
                    if best_match.funded_by:
                        print('Ya esta financiado')
                        # print("matched second", best_match.title, row["CDD Option"], row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"])
                    # print("Best match:", best_match.title, row["CDD Option"], row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"])
                    best_match.funded_by = project
                    best_match.longitude = row["Longitude (x)"]
                    best_match.latitude = row["Latitude (y)"]
                    best_match.imported_project_id = imported_project_id #'COSO' + str(row["ID"])
                    physical_execution_rate = row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"]
                    # check if physical_execution_rate is a number
                    physical_execution_rate = pd.to_numeric(physical_execution_rate, errors='coerce')
                    if pd.isna(physical_execution_rate):
                        physical_execution_rate = 0
                    try:
                        best_match.physical_execution_rate = int(float(physical_execution_rate))
                    except:
                        best_match.physical_execution_rate = 0

                    if row["status"] == "Identifié":
                        best_match.project_status = "F"
                    elif row["status"] == "En cours":
                        best_match.project_status = "P"
                    elif pd.isna(row["status"]):
                        best_match.project_status = "F"
                    elif row["status"] == "Arrêt":
                        best_match.project_status = "PA"
                    elif row["status"] in STRUCTURE_COMPLETED_STATUS: #elif row["status"] == "Achevé" or row["status"] == "Réception provisoire":
                        best_match.project_status = "C"
                    else:
                        best_match.project_status = "P"

                    if project:
                        best_match.came_from.add(project)
                    
                    cost = safe_float(row["COUT ESTIME DE L'OUVRAGE"])
                    if cost:
                        best_match.estimated_cost = cost

                    best_match.save()
                    count += 1
                    # Do something with the matched investment
                else:
                    # Handle the case where no similar investment is found
                    # print("No similar investment found for village:", row["village"], index)
                    not_matched += 1
            else:
                print("Village not found:", row["village"], index)
        creating = 0
        existing_with_village = 0
        similarity_threshold = 60
        for index, row in df.iterrows():
            village = AdministrativeLevel.objects.filter(
                name=row["village"],
                parent__name=row["parent_adm"],
                parent__parent__name=row["parent_parent_adm"],
            )
            if village.exists():
                imported_project_id = f'{project.name}.{row["ID"]}.{row["N"]}' # PROJECT_NAME.SUBPROJECT_KIT_NUMBER.NUMBER_INFRASTRUCTURE
                investments = Investment.objects.filter(administrative_level=village.first(), funded_by=project)
                matched_investments = [
                    investment for investment in investments
                    if fuzz.token_set_ratio(normalize_text(investment.title), normalize_text(row["CDD Option"] if safe_value(row["CDD Option"]) else row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])) >= similarity_threshold and (
                       investment.imported_project_id==imported_project_id or not investment.imported_project_id
                    )
                ]
                
                if not investments or not matched_investments:
                    creating += 1
                    sector = Sector.objects.all()
                    other_sector = Sector.objects.get(name="Autre")
                    matched_sectors = [
                        sec for sec in sector
                        if fuzz.token_set_ratio(normalize_text(sec.name), normalize_text(row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])) >= similarity_threshold
                    ]
                    # try:
                    #     cost = float(row["COUT ESTIME DE L'OUVRAGE"])
                    # except:
                    #     cost = 0
                    cost = safe_float(row["COUT ESTIME DE L'OUVRAGE"])

                    physical_execution_rate = row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"]
                    if pd.isna(physical_execution_rate):
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
                    elif row["status"] in STRUCTURE_COMPLETED_STATUS: #elif row["status"] == "Achevé" or row["status"] == "Réception provisoire":
                        project_status = "C"

                    try:
                        physical_execution_rate = int(float(physical_execution_rate))
                    except:
                        physical_execution_rate = 0

                    investment_created = Investment.objects.create(
                        title=(row["CDD Option"] if safe_value(row["CDD Option"]) else row["TYPE D'OUVRAGE (INFRASTRUCTURE)"]),
                        administrative_level=village.first(),
                        funded_by=project,
                        longitude=row["Longitude (x)"],
                        latitude=row["Latitude (y)"],
                        project_status=project_status,
                        sector=matched_sectors[0] if matched_sectors else other_sector,
                        estimated_cost=cost,
                        duration=0,
                        delays_consumed=0,
                        physical_execution_rate=physical_execution_rate,
                        financial_implementation_rate=0,
                        imported_project_id=imported_project_id
                    )

                    if project:
                        investment_created.came_from.add(project)
                        investment_created.save()

                else:
                    existing_with_village += 1
                    print(investments.first().funded_by)

            # Example: Just print the row, you should replace this with your actual processing logic
            #print(row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])

        # Example: Updating the project with some information (pseudo-code)
        # project.some_field = some_value_based_on_excel_data
        # project.save()
        print(count)
        print(f'created amount {creating}')
        print(f'existing with village {existing_with_village}')
        self.stdout.write(self.style.SUCCESS('Successfully processed the Excel file for project ID "%s"' % project_id))