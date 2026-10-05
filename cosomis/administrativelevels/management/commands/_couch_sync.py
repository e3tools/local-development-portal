"""Shared plumbing for the commands that read the facilitator CouchDB
databases: the --validated option every command reading task documents takes,
and the sync of 5_synctasks and 9_syncattachments.

Each facilitator database is read with a single Mango query, and its documents
are matched against rows loaded up front, so a run costs a handful of SQL
queries per facilitator database instead of several per document.

Every CouchDB document maps to exactly one row per village, keyed on
(village, no_sql_db_id). The project is deliberately not part of that key:
phases synced before Phase.project existed must be updated in place. When the
project was part of the key, re-syncing copied every phase, activity and task,
and the attachments stayed on the old copies, which no page displays.
"""
from collections import Counter
from datetime import datetime

from django.db.models import F
from django.utils import timezone

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project
from investments.models import Attachment

BATCH_SIZE = 500
COUCH_PAGE_SIZE = 1000
ATTACHMENT_URL_MAX_LENGTH = Attachment._meta.get_field('url').max_length
VALIDATED_CHOICES = ('true', 'false', 'none', 'all')


def add_validated_argument(parser):
    parser.add_argument(
        '--validated', nargs='+', choices=VALIDATED_CHOICES, default=['true'], metavar='{true,false,none,all}',
        help=(
            "Tasks CouchDB à lire selon leur champ validated : true (par défaut, tasks validées), "
            "false (rejetées), none (pas encore validées : champ absent ou null). Les valeurs se "
            "combinent, ex. --validated false none. all lit toutes les tasks."
        ),
    )


def validated_condition(values):
    """Mango condition on a task document's `validated` field for the
    --validated values, or None when every task must be read."""
    values = set(values)
    if 'all' in values or values >= {'true', 'false', 'none'}:
        return None
    conditions = []
    booleans = [value == 'true' for value in ('true', 'false') if value in values]
    if booleans:
        conditions.append({'validated': booleans[0] if len(booleans) == 1 else {'$in': booleans}})
    if 'none' in values:
        conditions += [{'validated': None}, {'validated': {'$exists': False}}]
    return conditions[0] if len(conditions) == 1 else {'$or': conditions}


def with_validated(task_selector, values):
    """`task_selector` restricted to the tasks the --validated values select."""
    condition = validated_condition(values)
    return task_selector if condition is None else {'$and': [task_selector, condition]}


class SyncReport:
    def __init__(self):
        self.counts = Counter()
        self.errors = []

    def error(self, document, reason):
        self.errors.append('%s %s (%s): %s' % (
            document.get('type'), document.get('_id'), document.get('name', ''), reason
        ))

    def merge(self, other):
        self.counts.update(other.counts)
        self.errors.extend(other.errors)

    def summary(self):
        return ', '.join('%s=%s' % item for item in sorted(self.counts.items())) or 'nothing to do'


def valid_facilitator_dbs(nsc):
    """Facilitator databases that hold field data (not develop or training mode)."""
    for db_name in nsc.list_all_databases('facilitator'):
        for document in nsc.get_db(db_name).get_query_result({"type": "facilitator"}):
            try:
                if not document['develop_mode'] and not document['training_mode']:
                    yield db_name
                    break
            except KeyError:
                break


def fetch_documents(nsc, db_name, types, fields=None, validated=('true',)):
    """Every document of the given types, grouped by type, in one query.
    `validated` (the --validated values) only filters the task documents."""
    grouped = {doc_type: [] for doc_type in types}
    if fields is not None:
        fields = sorted(set(fields) | {'type'})
    selector = {"type": {"$in": list(types)}}
    if 'task' in types and validated_condition(validated) is not None:
        others = [doc_type for doc_type in types if doc_type != 'task']
        selector = with_validated({"type": "task"}, validated)
        if others:
            selector = {"$or": [{"type": {"$in": others}}, selector]}
    result = nsc.get_db(db_name).get_query_result(selector, fields=fields, page_size=COUCH_PAGE_SIZE)
    for document in result:
        grouped[document['type']].append(document)
    return grouped


def adm_ids_by_couch_id():
    return dict(
        AdministrativeLevel.objects.filter(no_sql_db_id__isnull=False).values_list('no_sql_db_id', 'id')
    )


def project_ids_by_name():
    project_ids = {}
    for name, pk in Project.objects.order_by('id').values_list('name', 'id'):
        project_ids.setdefault(name.lower(), pk)
    return project_ids


def _lower(value):
    return (value or '').lower()


def _couch_datetime(value):
    """CouchDB task dates read like '2026-9-3 23:19:52' (no zero padding)."""
    try:
        return timezone.make_aware(datetime.strptime(value, '%Y-%m-%d %H:%M:%S'))
    except (TypeError, ValueError):
        return None


def _assign(obj, values, now):
    """Set `values` on `obj`. Return True if a field changed, so rows that did
    not change are left out of the bulk UPDATE."""
    changed = False
    for field, value in values.items():
        if getattr(obj, field) != value:
            setattr(obj, field, value)
            changed = True
    if changed:
        obj.updated_date = now  # bulk_update() bypasses auto_now
    return changed


def _save(model, to_create, to_update, fields, report):
    model.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
    model.objects.bulk_update(to_update, fields + ['updated_date'], batch_size=BATCH_SIZE)
    report.counts['%s created' % model._meta.model_name] += len(to_create)
    report.counts['%s updated' % model._meta.model_name] += len(to_update)


def _villages(documents, adm_ids, report):
    """Pair each document with its village pk, dropping unknown villages."""
    paired = []
    for document in documents:
        village_id = adm_ids.get(document.get('administrative_level_id'))
        if village_id is None:
            report.error(document, 'unknown administrative level')
        else:
            paired.append((village_id, document))
    return paired


def sync_planning_cycle(phase_docs, activity_docs, task_docs, adm_ids, project_ids, validated=('true',)):
    """Upsert one facilitator's phases, then activities, then tasks.
    `validated` is the --validated selection `task_docs` were read with."""
    report = SyncReport()
    now = timezone.now()
    phase_docs = _villages(phase_docs, adm_ids, report)
    activity_docs = _villages(activity_docs, adm_ids, report)
    task_docs = _villages(task_docs, adm_ids, report)
    village_ids = {village_id for village_id, _ in phase_docs + activity_docs + task_docs}
    if not village_ids:
        return report

    # Ordered by id so that, if duplicates are still present, the newest row
    # wins, which is also the row dedupe_planning_cycle keeps.
    phases = {
        (phase.village_id, phase.no_sql_db_id): phase
        for phase in Phase.objects.filter(village_id__in=village_ids, no_sql_db_id__isnull=False).order_by('id')
    }
    to_create, to_update = [], []
    for village_id, document in phase_docs:
        try:
            values = {'name': document['name'], 'description': document['description'], 'order': document['order']}
        except KeyError as e:
            report.error(document, 'missing field %s' % e)
            continue
        project_id = project_ids.get(_lower(document.get('project_name')))
        if project_id:
            values['project_id'] = project_id
        phase = phases.get((village_id, document['_id']))
        if phase is None:
            phase = Phase(village_id=village_id, no_sql_db_id=document['_id'], **values)
            phases[(village_id, document['_id'])] = phase
            to_create.append(phase)
        elif _assign(phase, values, now):
            to_update.append(phase)
    _save(Phase, to_create, to_update, ['name', 'description', 'order', 'project'], report)
    phases_by_pk = {phase.pk: phase for phase in phases.values()}

    activities = {
        (activity.village_pk, activity.no_sql_db_id): activity
        for activity in Activity.objects.filter(
            phase__village_id__in=village_ids, no_sql_db_id__isnull=False
        ).annotate(village_pk=F('phase__village_id')).order_by('id')
    }
    to_create, to_update = [], []
    for village_id, document in activity_docs:
        phase = phases.get((village_id, document.get('phase_id')))
        if phase is None:
            report.error(document, 'phase %s not found' % document.get('phase_id'))
            continue
        try:
            values = {
                'phase_id': phase.pk, 'name': document['name'],
                'description': document['description'], 'order': document['order'],
            }
        except KeyError as e:
            report.error(document, 'missing field %s' % e)
            continue
        activity = activities.get((village_id, document['_id']))
        if activity is None:
            activity = Activity(no_sql_db_id=document['_id'], **values)
            activities[(village_id, document['_id'])] = activity
            to_create.append(activity)
        elif _assign(activity, values, now):
            to_update.append(activity)
    _save(Activity, to_create, to_update, ['phase', 'name', 'description', 'order'], report)

    # Task documents normally point to their activity by id. A few only match by
    # name, and only within the same project. A name shared by two activities
    # is ambiguous and maps to None.
    activities_by_name = {}
    for (village_id, _), activity in activities.items():
        phase = phases_by_pk.get(activity.phase_id)
        key = (village_id, phase.project_id if phase else None, _lower(activity.name))
        activities_by_name[key] = None if key in activities_by_name else activity

    tasks = {
        (task.village_pk, task.no_sql_db_id): task
        for task in Task.objects.filter(
            activity__phase__village_id__in=village_ids, no_sql_db_id__isnull=False
        ).annotate(village_pk=F('activity__phase__village_id')).order_by('id')
    }
    to_create, to_update, seen = [], [], set()
    for village_id, document in task_docs:
        seen.add((village_id, document['_id']))
        activity = activities.get((village_id, document.get('activity_id')))
        if activity is None:
            activity = activities_by_name.get((
                village_id,
                project_ids.get(_lower(document.get('project_name'))),
                _lower(document.get('activity_name')),
            ))
        if activity is None:
            report.error(document, 'activity %s not found' % document.get('activity_id'))
            continue
        form_response = document.get('form_response', {})
        try:
            values = {
                'activity_id': activity.pk, 'name': document['name'],
                'description': document['description'], 'order': document['order'],
                'status': Task.COMPLETED if document['completed'] else (
                    Task.IN_PROGRESS if form_response else Task.NOT_STARTED
                ),
                'form_responses': form_response, 'form': document.get('form', ''),
                'validated': document.get('validated'),
                'date_validated': _couch_datetime(document.get('date_validated')),
            }
        except KeyError as e:
            report.error(document, 'missing field %s' % e)
            continue
        task = tasks.get((village_id, document['_id']))
        if task is None:
            task = Task(no_sql_db_id=document['_id'], **values)
            tasks[(village_id, document['_id'])] = task
            to_create.append(task)
        elif _assign(task, values, now):
            to_update.append(task)

    # When the selection includes validated tasks, a task still marked
    # validated here but absent from the result is no longer validated in
    # CouchDB (rejected or sent back for review): withdraw it, so pages that
    # only show validated work stop showing it.
    if 'true' in validated and validated_condition(validated) is not None:
        left_out = {'true', 'false', 'none'} - set(validated)
        withdrawn = False if left_out == {'false'} else None
        for key, task in tasks.items():
            if task.validated and key not in seen and _assign(task, {'validated': withdrawn}, now):
                to_update.append(task)
                report.counts['task validation withdrawn'] += 1
    _save(
        Task, to_create, to_update,
        ['activity', 'name', 'description', 'order', 'status', 'form_responses', 'form',
         'validated', 'date_validated'],
        report,
    )
    return report


def sync_task_attachments(task_docs, adm_ids):
    """Create the Attachment rows that a facilitator's task documents point to.

    Running it again creates nothing new. Attachments are matched on the
    task's CouchDB id, not its pk, so an attachment already stored on another
    copy of the same task (rows dedupe_planning_cycle has not merged yet) is
    moved onto the task kept instead of being stored again. An attachment that
    an earlier run saved without its task (task=None, same village and url)
    gets its task set in place.

    Attachment.name holds the label the task document gives the file (e.g.
    "Photo de la rencontre"), which tells apart the files of one task.
    """
    report = SyncReport()
    task_docs = _villages(task_docs, adm_ids, report)
    village_ids = {village_id for village_id, _ in task_docs}
    if not village_ids:
        return report

    tasks = {
        (task.village_pk, task.no_sql_db_id): task
        for task in Task.objects.filter(
            activity__phase__village_id__in=village_ids, no_sql_db_id__isnull=False
        ).annotate(village_pk=F('activity__phase__village_id')).only('id', 'order', 'no_sql_db_id').order_by('id')
    }
    # Ordered by id so the newest copy of a duplicated attachment is the one kept.
    stored = {
        (attachment.village_pk, attachment.task_couch_id, attachment.url): attachment
        for attachment in Attachment.objects.filter(
            task__activity__phase__village_id__in=village_ids
        ).annotate(
            village_pk=F('task__activity__phase__village_id'), task_couch_id=F('task__no_sql_db_id')
        ).only('id', 'task_id', 'url', 'name', 'order').order_by('id')
    }
    stored_urls = {(village_id, url) for village_id, _, url in stored}
    orphans = {}
    for attachment in Attachment.objects.filter(
        adm_id__in=village_ids, task__isnull=True, investment__isnull=True
    ).only('id', 'adm_id', 'url', 'task_id', 'name', 'order').order_by('-id'):
        orphans.setdefault((attachment.adm_id, attachment.url), attachment)

    now = timezone.now()
    to_create, to_update = [], []
    for village_id, document in task_docs:
        task = tasks.get((village_id, document['_id']))
        for entry in document.get('attachments') or []:
            url = (entry.get('attachment') or {}).get('uri')
            if not url:
                continue
            if len(url) > ATTACHMENT_URL_MAX_LENGTH:
                report.error(document, 'attachment url longer than %s characters' % ATTACHMENT_URL_MAX_LENGTH)
                continue
            name = entry.get('name') or None
            if task is None:
                if (village_id, url) in orphans or (village_id, url) in stored_urls:
                    continue
                attachment = Attachment(adm_id=village_id, url=url, name=name)
                orphans[(village_id, url)] = attachment
            else:
                key = (village_id, task.no_sql_db_id, url)
                existing = stored.get(key) or orphans.pop((village_id, url), None)
                stored_urls.add((village_id, url))
                values = {'task_id': task.pk, 'name': name, 'order': task.order or 0}
                if existing is not None:
                    # pk is None when it is already queued for creation
                    if _assign(existing, values, now) and existing.pk is not None:
                        to_update.append(existing)
                    stored[key] = existing
                    continue
                attachment = Attachment(adm_id=village_id, url=url, **values)
                stored[key] = attachment
            attachment.type = Attachment.PHOTO if 'photo' in _lower(entry.get('name')) else Attachment.DOCUMENT
            to_create.append(attachment)
    _save(Attachment, to_create, to_update, ['task', 'name', 'order'], report)
    return report
