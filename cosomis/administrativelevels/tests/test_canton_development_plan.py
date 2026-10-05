"""The canton profile shows the canton development plan: the file uploaded
under CANTON_PLAN_ATTACHMENT_NAME on a validated cantonal arbitration task of
one of its villages, like the village profile shows its development plan."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project
from administrativelevels.services.canton_summary_service import (
    CANTON_PLAN_ATTACHMENT_NAME, CANTON_PLAN_TASK_NAMES, CantonSummaryService,
)
from investments.models import Attachment

User = get_user_model()
COSO_TASK, FA_COSO_TASK, _ = CANTON_PLAN_TASK_NAMES


class CantonDevelopmentPlanTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='agent@email.com', email='agent@email.com', password='x', is_approved=True
        )
        self.coso = Project.objects.create(name='COSO', owner=self.user)
        self.fa_coso = Project.objects.create(name='FA-COSO', owner=self.user)
        self.canton = AdministrativeLevel.objects.create(name='Canton', type=AdministrativeLevel.CANTON)
        self.village = self._village('Village A')

    def _village(self, name, canton=None):
        return AdministrativeLevel.objects.create(
            name=name, type=AdministrativeLevel.VILLAGE, parent=canton or self.canton, is_headquarters=True
        )

    def _plan(self, url, village=None, project=None, task_name=COSO_TASK, validated=True,
              date_validated=datetime(2026, 9, 3, tzinfo=timezone.utc), name=CANTON_PLAN_ATTACHMENT_NAME):
        phase = Phase.objects.create(village=village or self.village, project=project or self.coso,
                                     name='PLANIFICATION', description='', order=3)
        activity = Activity.objects.create(phase=phase, name='Deuxième journée de la réunion cantonale',
                                           description='', order=1)
        task = Task.objects.create(activity=activity, name=task_name, description='', order=1,
                                   validated=validated, date_validated=date_validated)
        return Attachment.objects.create(adm=task.activity.phase.village, task=task, url=url, name=name)

    def _plans(self):
        return [(project, plan.url) for project, plan in CantonSummaryService(self.canton).get_development_plans()]


class GetDevelopmentPlansTests(CantonDevelopmentPlanTestBase):
    def test_latest_validated_plan_of_each_project(self):
        self._plan('https://s3/coso-old.pdf', date_validated=datetime(2025, 1, 1, tzinfo=timezone.utc))
        self._plan('https://s3/coso-new.pdf', village=self._village('Village B'))
        self._plan('https://s3/fa-coso.docx', project=self.fa_coso, task_name=FA_COSO_TASK)

        self.assertEqual(self._plans(), [('COSO', 'https://s3/coso-new.pdf'), ('FA-COSO', 'https://s3/fa-coso.docx')])

    def test_only_the_plan_file_of_a_validated_task_of_the_canton(self):
        self._plan('https://s3/rejected.pdf', validated=False)
        self._plan('https://s3/not-reviewed.pdf', validated=None)
        self._plan('https://s3/pv.pdf', name="Télecharger le PV de la reunion cantonale d'arbitrages")
        self._plan('https://s3/other-task.pdf', task_name='Elaboration du plan d\'action villageois (PAV)')
        self._plan('file:///data/user/0/plan.pdf')
        other_canton = AdministrativeLevel.objects.create(name='Other', type=AdministrativeLevel.CANTON)
        self._plan('https://s3/other-canton.pdf', village=self._village('Elsewhere', canton=other_canton))

        self.assertEqual(self._plans(), [])


class CantonPageTests(CantonDevelopmentPlanTestBase):
    def _page(self):
        self.client.force_login(self.user)
        with patch('investments.models.PackageQuerySet.get_active_cart') as cart:
            cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            return self.client.get(reverse('administrativelevels:canton_detail', args=[self.canton.pk]))

    def test_shows_a_download_link_to_the_plan(self):
        self._plan('https://s3/plan.pdf?AWSAccessKeyId=x&Signature=y')

        response = self._page()

        self.assertContains(response, 'Plan de Développement du Canton')
        self.assertContains(response, 'href="https://s3/plan.pdf"')

    def test_names_the_project_when_the_canton_has_several_plans(self):
        self._plan('https://s3/coso.pdf')
        self._plan('https://s3/fa-coso.pdf', project=self.fa_coso, task_name=FA_COSO_TASK)

        response = self._page()

        self.assertContains(response, 'Plan de Développement du Canton (COSO)')
        self.assertContains(response, 'Plan de Développement du Canton (FA-COSO)')

    def test_no_row_without_a_validated_plan(self):
        self._plan('https://s3/plan.pdf', validated=False)

        self.assertNotContains(self._page(), 'Plan de Développement du Canton')
