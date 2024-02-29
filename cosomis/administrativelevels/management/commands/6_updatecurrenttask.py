from django.core.management.base import BaseCommand, CommandError
import time
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from investments.models import Investment
from administrativelevels.models import AdministrativeLevel, Task, Activity, Phase


class Command(BaseCommand):
    help = 'Description of your command'

    def handle(self, *args, **options):
        # Your command logic here
        activities = Activity.objects.all().prefetch_related('phase__village')
        adms = AdministrativeLevel.objects.all()
        for adm in adms:
            village_activities = activities.filter(phase__village=adm).order_by('-order')
            for activity in village_activities:
                latest_tasks = Task.objects.filter(activity=activity).order_by('-order')
                previous = None
                for task in latest_tasks:
                    if task.status == 'completed' and previous is not None:
                        previous.status = 'in progress'
                        previous.save()
                        break
                    previous = task
                if Task.objects.filter(activity=activity, status='in progress'):
                    break
        self.stdout.write(self.style.SUCCESS('Successfully executed mycommand!'))



