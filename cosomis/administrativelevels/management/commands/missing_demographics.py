from django.core.management.base import BaseCommand, CommandError
import time
from administrativelevels.models import AdministrativeLevel, Task
import random

class Command(BaseCommand):
    help = 'Description of your command'

    def add_arguments(self, parser):
        # You can add command-line arguments here, if needed
        pass


    def handle(self, *args, **options):
        # Your command logic here
        tasks = Task.objects.filter(activity__phase__order=1, activity__order=2, order=4)
        for task in tasks:
            response = next((item['response'] for item in task.dict_form_responses if
                             item['label'] == 'Y a t – il combien de groupes ethniques dans le village ?'), None)
            if response:
                adm = task.activity.phase.village
                adm.population_minorities = response
                adm.save()
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))
