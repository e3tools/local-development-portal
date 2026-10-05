from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Case, Count, Max, Value, When

from administrativelevels.models import Phase, Activity, Task
from investments.models import Attachment

BATCH_SIZE = 500

# Each level, top-down: the model, the paths to its village and project, and
# the rows hanging from it that must be moved before a duplicate is deleted
# (Activity.phase, Task.activity and Attachment.task all CASCADE).
LEVELS = (
    (Phase, 'village_id', 'project_id', Activity, 'phase_id'),
    (Activity, 'phase__village_id', 'phase__project_id', Task, 'activity_id'),
    (Task, 'activity__phase__village_id', 'activity__phase__project_id', Attachment, 'task_id'),
)


def _chunks(items):
    items = list(items)
    for start in range(0, len(items), BATCH_SIZE):
        yield items[start:start + BATCH_SIZE]


def merge_duplicates(model, village_path, project_path, child_model, child_fk):
    """Collapse the rows that mirror the same CouchDB document in the same
    village onto one survivor (the newest row, preferring one tied to a
    project), moving their children onto it first.
    Returns (rows deleted, children moved)."""
    duplicated_ids = (
        model.objects.filter(no_sql_db_id__isnull=False)
        .values('no_sql_db_id').annotate(copies=Count('id')).filter(copies__gt=1)
        .values('no_sql_db_id')
    )
    groups = defaultdict(list)
    for pk, village_id, project_id, couch_id in model.objects.filter(
        no_sql_db_id__in=duplicated_ids
    ).values_list('id', village_path, project_path, 'no_sql_db_id').iterator(chunk_size=5000):
        groups[(village_id, couch_id)].append((project_id is not None, pk))

    survivor_of = {}
    for members in groups.values():
        if len(members) > 1:
            survivor = max(members)[1]
            survivor_of.update((pk, survivor) for _, pk in members if pk != survivor)

    moved = 0
    for chunk in _chunks(survivor_of.items()):
        moved += child_model.objects.filter(**{child_fk + '__in': [old for old, _ in chunk]}).update(
            **{child_fk: Case(*[When(**{child_fk: old}, then=Value(new)) for old, new in chunk])}
        )
    deleted = 0
    for chunk in _chunks(survivor_of):
        deleted += model.objects.filter(pk__in=chunk).only('pk').delete()[1].get(model._meta.label, 0)
    return deleted, moved


def delete_duplicate_attachments():
    """Delete the task attachments stored more than once, then the attachments
    left without a task whose url is already on a task. For each set of
    copies, the newest row is kept. Returns the number of rows deleted.

    Each step is one DELETE against an uncorrelated GROUP BY subquery: url is
    not indexed, so correlated EXISTS subqueries would rescan the table for
    every row."""
    on_task = Attachment.objects.filter(task__isnull=False)
    deleted = on_task.exclude(
        id__in=on_task.values('task_id', 'url').annotate(newest=Max('id')).values('newest')
    ).delete()[0]

    orphans = Attachment.objects.filter(task__isnull=True, investment__isnull=True)
    deleted += orphans.filter(url__in=on_task.values('url')).delete()[0]
    deleted += orphans.exclude(
        id__in=orphans.values('adm_id', 'url').annotate(newest=Max('id')).values('newest')
    ).delete()[0]
    return deleted


class Command(BaseCommand):
    help = (
        'Merge the Phase/Activity/Task rows duplicated by 5_synctasks, moving their '
        'attachments onto the rows kept, then delete duplicate attachments.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report the changes, then roll them back.')

    def handle(self, *args, dry_run=False, **options):
        with transaction.atomic():
            for model, village_path, project_path, child_model, child_fk in LEVELS:
                deleted, moved = merge_duplicates(model, village_path, project_path, child_model, child_fk)
                self.stdout.write('%s: %s duplicates deleted, %s %s rows moved onto the rows kept' % (
                    model.__name__, deleted, moved, child_model.__name__
                ))
            self.stdout.write('Attachment: %s duplicates deleted' % delete_duplicate_attachments())
            if dry_run:
                transaction.set_rollback(True)
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: every change has been rolled back.'))
        else:
            self.stdout.write(self.style.SUCCESS('Planning cycle deduplicated.'))
