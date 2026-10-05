"""The village and canton profiles show their development plan of each project:
the file uploaded under a given label on a validated planning task. One plan is
a direct download link; several open a modal listing them with their
validation date."""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import formats, translation

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project
from administrativelevels.services.canton_summary_service import CantonSummaryService
from administrativelevels.services.development_plans import (
    CANTON_PLAN_ATTACHMENT_NAME, CANTON_PLAN_TASK_NAMES, VILLAGE_PLAN_ATTACHMENT_NAME, VILLAGE_PLAN_TASK_NAMES,
    village_development_plans,
)
from investments.models import Attachment

User = get_user_model()
COSO_CANTON_TASK, FA_COSO_CANTON_TASK, _ = CANTON_PLAN_TASK_NAMES
VILLAGE_TASK, = VILLAGE_PLAN_TASK_NAMES
SEPT_3 = datetime(2026, 9, 3, tzinfo=timezone.utc)
MODAL_LINK = 'data-target="#developmentPlansModal"'


def _shown(day):
    """How the modal prints a validation date (the site is in French)."""
    with translation.override('fr'):
        return formats.date_format(day, 'SHORT_DATE_FORMAT')


class DevelopmentPlanTestBase(TestCase):
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

    def _plan(self, url, task_name, name, village=None, project=None, validated=True, date_validated=SEPT_3):
        phase = Phase.objects.create(village=village or self.village, project=project or self.coso,
                                     name='PLANIFICATION', description='', order=3)
        activity = Activity.objects.create(phase=phase, name='Réunion', description='', order=1)
        task = Task.objects.create(activity=activity, name=task_name, description='', order=1,
                                   validated=validated, date_validated=date_validated)
        return Attachment.objects.create(adm=phase.village, task=task, url=url, name=name)

    def _canton_plan(self, url, task_name=COSO_CANTON_TASK, name=CANTON_PLAN_ATTACHMENT_NAME, **kwargs):
        return self._plan(url, task_name, name, **kwargs)

    def _village_plan(self, url, task_name=VILLAGE_TASK, name=VILLAGE_PLAN_ATTACHMENT_NAME, **kwargs):
        return self._plan(url, task_name, name, **kwargs)

    def _get(self, url_name, pk):
        self.client.force_login(self.user)
        with patch('investments.models.PackageQuerySet.get_active_cart') as cart:
            cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            return self.client.get(reverse('administrativelevels:' + url_name, args=[pk]))


class CantonDevelopmentPlansTests(DevelopmentPlanTestBase):
    def _plans(self):
        return [(plan.project_name, plan.url) for plan in CantonSummaryService(self.canton).get_development_plans()]

    def test_latest_validated_plan_of_each_project(self):
        self._canton_plan('https://s3/coso-old.pdf', date_validated=datetime(2025, 1, 1, tzinfo=timezone.utc))
        self._canton_plan('https://s3/coso-new.pdf', village=self._village('Village B'))
        self._canton_plan('https://s3/fa-coso.docx', project=self.fa_coso, task_name=FA_COSO_CANTON_TASK)

        self.assertEqual(self._plans(), [('COSO', 'https://s3/coso-new.pdf'), ('FA-COSO', 'https://s3/fa-coso.docx')])

    def test_only_the_plan_file_of_a_validated_task_of_the_canton(self):
        self._canton_plan('https://s3/rejected.pdf', validated=False)
        self._canton_plan('https://s3/not-reviewed.pdf', validated=None)
        self._canton_plan('https://s3/pv.pdf', name="Télecharger le PV de la reunion cantonale d'arbitrages")
        self._canton_plan('https://s3/village-plan.pdf', task_name=VILLAGE_TASK)
        self._canton_plan('file:///data/user/0/plan.pdf')
        other_canton = AdministrativeLevel.objects.create(name='Other', type=AdministrativeLevel.CANTON)
        self._canton_plan('https://s3/other-canton.pdf', village=self._village('Elsewhere', canton=other_canton))

        self.assertEqual(self._plans(), [])

    def test_page_links_the_only_plan_directly_in_a_new_tab(self):
        self._canton_plan('https://s3/plan.pdf?AWSAccessKeyId=x&Signature=y')

        response = self._get('canton_detail', self.canton.pk)

        self.assertContains(response, 'Plan de Développement du Canton')
        self.assertContains(response, 'href="https://s3/plan.pdf" target="_blank"')
        self.assertNotContains(response, MODAL_LINK)

    def test_page_lists_several_plans_in_a_modal_with_their_validation_date(self):
        self._canton_plan('https://s3/coso.pdf')
        feb_1 = datetime(2026, 2, 1, tzinfo=timezone.utc)
        self._canton_plan('https://s3/fa-coso.pdf', project=self.fa_coso, task_name=FA_COSO_CANTON_TASK,
                          date_validated=feb_1)

        response = self._get('canton_detail', self.canton.pk)

        self.assertContains(response, MODAL_LINK)
        self.assertContains(response, 'id="developmentPlansModal"')
        for text in ('COSO', _shown(SEPT_3), 'href="https://s3/coso.pdf" target="_blank"',
                     'FA-COSO', _shown(feb_1), 'href="https://s3/fa-coso.pdf" target="_blank"'):
            self.assertContains(response, text)

    def test_page_has_no_row_without_a_validated_plan(self):
        self._canton_plan('https://s3/plan.pdf', validated=False)

        self.assertNotContains(self._get('canton_detail', self.canton.pk), 'Plan de Développement du Canton')


class VillageDevelopmentPlansTests(DevelopmentPlanTestBase):
    def _plans(self):
        return [(plan.project_name, plan.url) for plan in village_development_plans(self.village)]

    def test_validated_plan_of_each_project(self):
        self._village_plan('https://s3/coso.pdf')
        self._village_plan('https://s3/fa-coso.pdf', project=self.fa_coso)

        self.assertEqual(self._plans(), [('COSO', 'https://s3/coso.pdf'), ('FA-COSO', 'https://s3/fa-coso.pdf')])

    def test_only_the_plan_file_of_a_validated_task_of_the_village(self):
        self._village_plan('https://s3/rejected.pdf', validated=False)
        self._village_plan('https://s3/photo.jpg', name='Photo de séance')
        self._village_plan('https://s3/canton-plan.pdf', task_name=COSO_CANTON_TASK)
        self._village_plan('https://s3/neighbour.pdf', village=self._village('Village B'))

        self.assertEqual(self._plans(), [])

    def test_page_links_the_only_plan_directly_in_a_new_tab(self):
        self._village_plan('https://s3/plan.pdf')

        response = self._get('village_detail', self.village.pk)

        self.assertContains(response, 'Plan de Développement du Village')
        self.assertContains(response, 'href="https://s3/plan.pdf" target="_blank"')
        self.assertNotContains(response, MODAL_LINK)

    def test_page_lists_several_plans_in_a_modal_with_their_validation_date(self):
        self._village_plan('https://s3/coso.pdf')
        self._village_plan('https://s3/fa-coso.pdf', project=self.fa_coso)

        response = self._get('village_detail', self.village.pk)

        self.assertContains(response, MODAL_LINK)
        for text in (_shown(SEPT_3), 'href="https://s3/coso.pdf" target="_blank"',
                     'href="https://s3/fa-coso.pdf" target="_blank"'):
            self.assertContains(response, text)
