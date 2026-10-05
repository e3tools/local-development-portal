"""Re-syncing the planning cycle must update rows in place, and attachments
must stay on the tasks the village page displays.

Before the fix, 5_synctasks included Phase.project in its lookup. Phases
synced before that field existed (project=NULL) were therefore copied with
their activities and tasks, and the attachments stayed on the old copies.
"""
from datetime import datetime, timezone as dt_timezone
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from administrativelevels.management.commands._couch_sync import (
    sync_planning_cycle, sync_task_attachments,
)
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project
from administrativelevels.views import build_planning_cycle
from investments.models import Attachment

User = get_user_model()

PHOTO_URL = 'https://bucket.s3.amazonaws.com/photo-1.jpg'


def _documents(project_name='PURS'):
    common = {'administrative_level_id': 'couch-village', 'project_name': project_name}
    phase = dict(common, _id='couch-phase', type='phase', name='Phase 1', description='', order=1)
    activity = dict(common, _id='couch-activity', type='activity', phase_id='couch-phase',
                    name='Activity 1', description='', order=1)
    task = dict(common, _id='couch-task', type='task', activity_id='couch-activity',
                activity_name='Activity 1', name='Task 1', description='', order=1,
                completed=True, form_response=[{'q': 'a'}], form=[],
                validated=True, date_validated='2026-9-3 23:19:52',
                attachments=[{'name': 'Photo de la rencontre', 'attachment': {'uri': PHOTO_URL}}])
    return [phase], [activity], [task]


class PlanningCycleSyncTestBase(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username='owner@email.com', email='owner@email.com', password='testpass123')
        self.project = Project.objects.create(name='PURS', owner=owner)
        self.village = AdministrativeLevel.objects.create(
            name='Village', type=AdministrativeLevel.VILLAGE, no_sql_db_id='couch-village'
        )
        self.adm_ids = {'couch-village': self.village.pk}
        self.project_ids = {'purs': self.project.pk}

    def _chain(self, project=None):
        phase = Phase.objects.create(village=self.village, project=project, no_sql_db_id='couch-phase',
                                     name='Phase 1', description='', order=1)
        activity = Activity.objects.create(phase=phase, no_sql_db_id='couch-activity',
                                           name='Activity 1', description='', order=1)
        task = Task.objects.create(activity=activity, no_sql_db_id='couch-task',
                                   name='Task 1', description='', order=1)
        return phase, activity, task


class SyncPlanningCycleTests(PlanningCycleSyncTestBase):
    def test_legacy_phase_without_project_is_updated_in_place(self):
        phase, _, task = self._chain(project=None)
        Attachment.objects.create(adm=self.village, task=task, url=PHOTO_URL, type=Attachment.PHOTO)

        report = sync_planning_cycle(*_documents(), self.adm_ids, self.project_ids)

        self.assertEqual(report.errors, [])
        self.assertEqual((Phase.objects.count(), Activity.objects.count(), Task.objects.count()), (1, 1, 1))
        phase.refresh_from_db()
        self.assertEqual(phase.project, self.project)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.COMPLETED)
        self.assertEqual(task.attachments.count(), 1)

    def test_second_run_creates_and_updates_nothing(self):
        sync_planning_cycle(*_documents(), self.adm_ids, self.project_ids)
        report = sync_planning_cycle(*_documents(), self.adm_ids, self.project_ids)

        self.assertEqual(sum(report.counts.values()), 0)
        self.assertEqual((Phase.objects.count(), Activity.objects.count(), Task.objects.count()), (1, 1, 1))

    def test_task_falls_back_to_its_activity_name_within_the_project(self):
        phases, activities, tasks = _documents()
        tasks[0]['activity_id'] = 'unknown-activity-id'

        report = sync_planning_cycle(phases, activities, tasks, self.adm_ids, self.project_ids)

        self.assertEqual(report.errors, [])
        self.assertEqual(Task.objects.get().activity.no_sql_db_id, 'couch-activity')

    def test_document_of_an_unknown_village_is_reported_not_raised(self):
        phases, activities, tasks = _documents()
        phases[0]['administrative_level_id'] = 'elsewhere'

        report = sync_planning_cycle(phases, activities, tasks, self.adm_ids, self.project_ids)

        self.assertEqual(Phase.objects.count(), 0)
        self.assertEqual(len(report.errors), 3)  # the phase, then its activity, then its task

    def test_review_of_the_task_is_copied(self):
        sync_planning_cycle(*_documents(), self.adm_ids, self.project_ids)

        task = Task.objects.get()
        self.assertIs(task.validated, True)
        self.assertEqual(task.date_validated, datetime(2026, 9, 3, 23, 19, 52, tzinfo=dt_timezone.utc))

    def test_validation_is_withdrawn_from_a_task_no_longer_validated(self):
        # Read with the default --validated true, a task validated earlier but
        # rejected since is simply absent from the result.
        cases = {('true',): None, ('true', 'none'): False}
        for validated, expected in cases.items():
            with self.subTest(validated=validated):
                Task.objects.all().delete()
                _, _, task = self._chain(project=self.project)
                Task.objects.filter(pk=task.pk).update(validated=True)
                phases, activities, _ = _documents()

                report = sync_planning_cycle(phases, activities, [], self.adm_ids, self.project_ids, validated)

                task.refresh_from_db()
                self.assertIs(task.validated, expected)
                self.assertEqual(report.counts['task validation withdrawn'], 1)


class SyncTaskAttachmentsTests(PlanningCycleSyncTestBase):
    def test_running_twice_stores_the_attachment_once(self):
        _, _, task = self._chain(project=self.project)
        _, _, task_docs = _documents()

        sync_task_attachments(task_docs, self.adm_ids)
        sync_task_attachments(task_docs, self.adm_ids)

        attachment = Attachment.objects.get()
        self.assertEqual((attachment.task, attachment.adm, attachment.type), (task, self.village, Attachment.PHOTO))
        self.assertEqual(attachment.name, 'Photo de la rencontre')

    def test_attachment_stored_under_the_task_name_gets_its_couchdb_label(self):
        _, _, task = self._chain(project=self.project)
        attachment = Attachment.objects.create(adm=self.village, task=task, url=PHOTO_URL, name='Task 1')
        _, _, task_docs = _documents()

        report = sync_task_attachments(task_docs, self.adm_ids)

        attachment.refresh_from_db()
        self.assertEqual(attachment.name, 'Photo de la rencontre')
        self.assertEqual((report.counts['attachment created'], report.counts['attachment updated']), (0, 1))

    def test_attachment_on_an_unmerged_copy_of_the_task_is_moved_not_copied(self):
        # dedupe_planning_cycle has not run yet: the attachment is still on the
        # legacy copy of the task, and the sync works on the newest copy.
        _, _, old_task = self._chain(project=None)
        _, _, new_task = self._chain(project=self.project)
        attachment = Attachment.objects.create(adm=self.village, task=old_task, url=PHOTO_URL)
        _, _, task_docs = _documents()

        report = sync_task_attachments(task_docs, self.adm_ids)

        self.assertEqual(report.counts['attachment created'], 0)
        self.assertEqual(Attachment.objects.get().pk, attachment.pk)
        attachment.refresh_from_db()
        self.assertEqual(attachment.task, new_task)

    def test_attachment_saved_without_its_task_is_relinked_in_place(self):
        _, _, task = self._chain(project=self.project)
        orphan = Attachment.objects.create(adm=self.village, task=None, url=PHOTO_URL, type=Attachment.PHOTO)
        _, _, task_docs = _documents()

        sync_task_attachments(task_docs, self.adm_ids)

        self.assertEqual(Attachment.objects.get().pk, orphan.pk)
        orphan.refresh_from_db()
        self.assertEqual(orphan.task, task)


class DedupePlanningCycleTests(PlanningCycleSyncTestBase):
    def setUp(self):
        super().setUp()
        # The state left by the old 5_synctasks: a legacy chain holding the
        # attachment, and a newer copy tied to the project, without it.
        self.old_phase, _, self.old_task = self._chain(project=None)
        self.new_phase, _, self.new_task = self._chain(project=self.project)
        self.attachment = Attachment.objects.create(
            adm=self.village, task=self.old_task, url=PHOTO_URL, type=Attachment.PHOTO
        )

    def test_keeps_the_new_rows_and_moves_attachments_onto_them(self):
        call_command('dedupe_planning_cycle', stdout=StringIO())

        self.assertEqual(list(Phase.objects.values_list('pk', flat=True)), [self.new_phase.pk])
        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(list(Task.objects.values_list('pk', flat=True)), [self.new_task.pk])
        self.attachment.refresh_from_db()
        self.assertEqual(self.attachment.task_id, self.new_task.pk)

    def test_deletes_duplicate_and_orphaned_copies_of_an_attachment(self):
        Attachment.objects.create(adm=self.village, task=self.new_task, url=PHOTO_URL)
        Attachment.objects.create(adm=self.village, task=None, url=PHOTO_URL)
        unrelated = Attachment.objects.create(adm=self.village, task=None, url='https://bucket/other.jpg')

        call_command('dedupe_planning_cycle', stdout=StringIO())

        self.assertEqual(Attachment.objects.filter(url=PHOTO_URL).count(), 1)
        self.assertTrue(Attachment.objects.filter(pk=unrelated.pk).exists())

    def test_dry_run_changes_nothing(self):
        call_command('dedupe_planning_cycle', dry_run=True, stdout=StringIO())

        self.assertEqual(Phase.objects.count(), 2)
        self.assertEqual(Task.objects.count(), 2)
        self.attachment.refresh_from_db()
        self.assertEqual(self.attachment.task_id, self.old_task.pk)


class ResyncAttachmentsTests(PlanningCycleSyncTestBase):
    def test_attachment_takes_its_task_village(self):
        _, _, task = self._chain(project=self.project)
        other = AdministrativeLevel.objects.create(name='Other', type=AdministrativeLevel.VILLAGE)
        misplaced = Attachment.objects.create(adm=other, task=task, url=PHOTO_URL)
        unset = Attachment.objects.create(adm=None, task=task, url='https://bucket/2.jpg')

        call_command('resync_attachments', stdout=StringIO())

        misplaced.refresh_from_db()
        unset.refresh_from_db()
        self.assertEqual((misplaced.adm_id, unset.adm_id), (self.village.pk, self.village.pk))


class TaskDetailAjaxViewTests(PlanningCycleSyncTestBase):
    def setUp(self):
        super().setUp()
        _, _, task = self._chain(project=self.project)
        Attachment.objects.create(adm=self.village, task=task, url=PHOTO_URL, type=Attachment.PHOTO)
        self.url = reverse('administrativelevels:utils:task_detail', args=[task.pk])

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(PHOTO_URL, response.content.decode())

    def test_user_awaiting_approval_is_forbidden(self):
        self.client.force_login(User.objects.create_user(
            username='pending@email.com', email='pending@email.com', password='x', is_approved=False
        ))

        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_approved_user_sees_the_task_attachments(self):
        self.client.force_login(User.objects.create_user(
            username='agent@email.com', email='agent@email.com', password='x', is_approved=True
        ))

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, PHOTO_URL)


class BuildPlanningCycleTests(PlanningCycleSyncTestBase):
    def test_whole_cycle_is_loaded_in_three_queries_in_order(self):
        phase, activity, _ = self._chain(project=self.project)
        Task.objects.create(activity=activity, no_sql_db_id='couch-task-0', name='Task 0',
                            description='', order=0, status=Task.COMPLETED)
        Activity.objects.create(phase=phase, name='Activity 2', description='', order=2)

        with self.assertNumQueries(3):
            phases = build_planning_cycle(self.village, self.project)

        activities = phases[0]['activities']
        self.assertEqual([a['name'] for a in activities], ['Activity 1', 'Activity 2'])
        self.assertEqual([t['name'] for t in activities[0]['tasks']], ['Task 0', 'Task 1'])
        self.assertEqual(activities[0]['status'], Task.COMPLETED)
