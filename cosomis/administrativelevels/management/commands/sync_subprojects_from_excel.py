import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from administrativelevels.models import Project, AdministrativeLevel
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
        similarity_threshold = 70  # For matching the investment title
        count = 0
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
                    if fuzz.ratio(investment.title, row["TYPE D'OUVRAGE (INFRASTRUCTURE)"]) >= similarity_threshold
                ]

                # Sort by similarity if you want the best match first
                matched_investments.sort(key=lambda inv: fuzz.ratio(inv.title, row["TYPE D'OUVRAGE (INFRASTRUCTURE)"]),
                                         reverse=True)

                if matched_investments:
                    best_match = matched_investments[0]  # The best match based on similarity
                    print("Best match:", best_match.title, row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])
                    count += 1
                    # Do something with the matched investment
                else:
                    # Handle the case where no similar investment is found
                    # print("No similar investment found for village:", row["village"], index)
                    pass
            else:
                print("Village not found:", row["village"], index)
            # Example: Just print the row, you should replace this with your actual processing logic
            #print(row["TYPE D'OUVRAGE (INFRASTRUCTURE)"])

        # Example: Updating the project with some information (pseudo-code)
        # project.some_field = some_value_based_on_excel_data
        # project.save()
        print(count)
        self.stdout.write(self.style.SUCCESS('Successfully processed the Excel file for project ID "%s"' % project_id))