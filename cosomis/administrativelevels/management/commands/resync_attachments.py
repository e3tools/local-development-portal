from django.core.management.base import BaseCommand
from django.db.models import F, OuterRef, Subquery

from administrativelevels.models import Task
from investments.models import Attachment


class Command(BaseCommand):
    help = "Set each task attachment's administrative level to its task's village"

    def handle(self, *args, **options):
        updated = Attachment.objects.filter(task__isnull=False).exclude(
            adm_id=F('task__activity__phase__village_id')
        ).update(adm_id=Subquery(
            Task.objects.filter(pk=OuterRef('task_id')).values('activity__phase__village_id')[:1]
        ))
        self.stdout.write(self.style.SUCCESS('Successfully synced attachments! (%s updated)' % updated))
