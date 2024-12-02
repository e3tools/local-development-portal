from django.core.management.base import BaseCommand, CommandError
import time
from administrativelevels.models import AdministrativeLevel
from investments.models import Investment


class Command(BaseCommand):
    help = 'Description of your command'
    count = 0

    def add_arguments(self, parser):
        # You can add command-line arguments here, if needed
        pass

    # checks if there are one or more investments with the same name
    def check_investments_title(self, investments):
        for investment in investments:
            duplicated = investments.filter(title=investment.title)
            if duplicated.count() > 1:
                self.count += 1
                print('Investment with the same name:', investment.title)
                for duplicated_investment in duplicated:
                    print(duplicated_investment.id)

    def handle(self, *args, **options):
        # Your command logic here
        administrative_levels = AdministrativeLevel.objects.filter(type=AdministrativeLevel.VILLAGE)

        for village in administrative_levels:
            investments = Investment.objects.filter(administrative_level=village)
            if investments.count() > 3:
                self.check_investments_title(investments)
        print('Total villages with more than 3 priorities:', self.count)
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
