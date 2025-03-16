from django.core.management.base import BaseCommand, CommandError
from no_sql_client import NoSQLClient
from cloudant.result import Result
from cloudant.document import Document
from administrativelevels.models import AdministrativeLevel, Task
from investments.models import Attachment


class Command(BaseCommand):
    help = 'Take attachments from task documents and change the adminsitrative level'


    def handle(self, *args, **options):
        attachments = Attachment.objects.all()
        for attachment in attachments:
            if attachment.task:
                attachment.adm = attachment.task.activity.phase.village
                attachment.save()
        self.stdout.write(self.style.SUCCESS('Successfully synced attachments!'))

