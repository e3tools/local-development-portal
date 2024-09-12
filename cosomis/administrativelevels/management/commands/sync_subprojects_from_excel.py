import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel, Sector
from investments.models import Investment
from thefuzz import fuzz


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
                # Iterate over the Investment objects and calculate the similarity
                investments = Investment.objects.filter(administrative_level=village.first())
                # Filter by similarity manually
                matched_investments = [
                    investment for investment in investments
                    if fuzz.ratio(investment.title, row["CDD Option"]) >= similarity_threshold
                ]

                # Sort by similarity if you want the best match first
                matched_investments.sort(key=lambda inv: fuzz.ratio(inv.title, row["CDD Option"]),
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
                    if row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"] == "Approuvé":
                        best_match.project_status = "F"
                    elif row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"] == "En cours":
                        best_match.project_status = "P"
                    elif pd.isna(row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"]):
                        best_match.project_status = "F"
                    elif row["NIVEAU ACTUEL DE REALISATION PHYSIQUE DE L'OUVRAGE"] == "Interrompu":
                        best_match.project_status = "PA"
                    else:
                        best_match.project_status = "P"
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
        for index, row in df.iterrows():
            village = AdministrativeLevel.objects.filter(
                name=row["village"],
                parent__name=row["parent_adm"],
                parent__parent__name=row["parent_parent_adm"],
            )
            exists = Investment.objects.filter(administrative_level=village.first(), funded_by=project)
            if not exists:
                creating += 1
                sector = Sector.objects.all()
                other_sector = Sector.objects.get(name="Autre")
                similarity_threshold = 60
                matched_sectors = [
                    sec for sec in sector
                    if fuzz.ratio(sec.name, row["TYPE D'OUVRAGE (INFRASTRUCTURE)"]) >= similarity_threshold
                ]
                try:
                    cost = float(row["COUT ESTIME DE L'OUVRAGE"])
                except:
                    cost = 0
                Investment.objects.create(
                    title=row["CDD Option"],
                    administrative_level=village.first(),
                    funded_by=project,
                    longitude=row["Longitude (x)"],
                    latitude=row["Latitude (y)"],
                    project_status="F",
                    sector=matched_sectors[0] if matched_sectors else other_sector,
                    estimated_cost=cost,
                    duration=0,
                    delays_consumed=0,
                    physical_execution_rate=0,
                    financial_implementation_rate=0
                )
            else:
                existing_with_village += 1
                print(exists.first().funded_by)

            # Example: Just print the row, you should replace this with your actual processing logic
            #print(row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])

        # Example: Updating the project with some information (pseudo-code)
        # project.some_field = some_value_based_on_excel_data
        # project.save()
        print(count)
        print(f'created amount {creating}')
        print(f'existing with village {existing_with_village}')
        self.stdout.write(self.style.SUCCESS('Successfully processed the Excel file for project ID "%s"' % project_id))