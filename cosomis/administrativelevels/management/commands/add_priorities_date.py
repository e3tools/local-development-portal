from django.core.management.base import BaseCommand, CommandError
import time
from administrativelevels.models import AdministrativeLevel, Task
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Description of your command'

    def add_arguments(self, parser):
        # You can add command-line arguments here, if needed
        pass

    def random_date(self, start_date, end):
        delta = end - start_date
        random_days = random.randint(0, delta.days)
        return start_date + timedelta(days=random_days)

    def handle(self, *args, **options):
        # Your command logic here
        start_date = datetime(2022, 11, 30)
        end_date = datetime(2023, 3, 30)
        tasks = Task.objects.filter(activity__phase__order=3, activity__order=1, order=8)
        for task in tasks:
            response = next((item['response'] for item in task.dict_form_responses if
                             item['label'] == 'Y a t – il combien de groupes ethniques dans le village ?'), None)
            response = None
            if response:
                adm = task.activity.phase.village
                adm.identified_priority = response
                adm.save()
            else:
                # generate a randon number from 1 to 4
                random_generated_date = self.random_date(start_date, end_date)
                adm = task.activity.phase.village
                adm.identified_priority = random_generated_date
                print(adm.identified_priority)
                adm.save()
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
