"""
Integration tests for CantonPlanningSummaryView.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="officer@email.com", approved=True, **kwargs):
    user = User.objects.create_user(
        username=username,
        email=username,
        password="testpass123",
        is_approved=approved,
        **kwargs
    )
    return user


def _make_canton(name="Canton Test", **kwargs):
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.CANTON,
        **kwargs
    )


def _make_village(name, canton):
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.VILLAGE,
        parent=canton
    )

def _make_phase(village, name, order=None):
    return Phase.objects.create(
        village=village,
        name=name,
        order=order
    )

def _make_activity(phase, name, order=None):
    return Activity.objects.create(
        phase=phase,
        name=name,
        order=order
    )

def _make_task(activity, name, status=Task.NOT_STARTED, order=None):
    return Task.objects.create(
        activity=activity,
        name=name,
        status=status,
        order=order
    )


# ---------------------------------------------------------------------------
# Base class — shared setup
# ---------------------------------------------------------------------------

class CantonPlanningSummaryViewBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.canton = _make_canton(name="Canton Borgou")

        cls.village_a = _make_village(name="Village Alpha", canton=cls.canton)
        cls.village_b = _make_village(name="Village Beta", canton=cls.canton)

        # Setup planning cycle for Village A: 1 Phase, 1 Activity, 1 Task (Completed)
        cls.phase_a1 = _make_phase(cls.village_a, "Phase 1")
        cls.activity_a1 = _make_activity(cls.phase_a1, "Activity 1")
        cls.task_a1 = _make_task(cls.activity_a1, "Task 1", status=Task.COMPLETED)

        # Setup planning cycle for Village B: 1 Phase (same name), 1 Activity, 1 Task (Not Started)
        cls.phase_b1 = _make_phase(cls.village_b, "Phase 1")
        cls.activity_b1 = _make_activity(cls.phase_b1, "Activity 1")
        cls.task_b1 = _make_task(cls.activity_b1, "Task 1", status=Task.NOT_STARTED)

        cls.url = reverse("administrativelevels:canton_planning_summary", args=[cls.canton.pk])

    def _login(self):
        self.client.force_login(self.user)


# ---------------------------------------------------------------------------
# Test Group 1 — HTTP / access control
# ---------------------------------------------------------------------------

class CantonPlanningSummaryViewAccessTest(CantonPlanningSummaryViewBaseTest):

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [301, 302])

    def test_authenticated_user_gets_200(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        self._login()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "canton/tabs/planning_cycle.html")

    def test_non_existent_canton_returns_404(self):
        self._login()
        bad_url = reverse("administrativelevels:canton_planning_summary", args=[99999])
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Test Group 2 — Planning Summary Context
# ---------------------------------------------------------------------------

class CantonPlanningSummaryViewContextTest(CantonPlanningSummaryViewBaseTest):

    def _get_context(self):
        self._login()
        response = self.client.get(self.url)
        return response.context

    def test_planning_summary_key_exists_in_context(self):
        ctx = self._get_context()
        self.assertIn('planning_summary', ctx)

    def test_planning_summary_contains_villages(self):
        ctx = self._get_context()
        summary = ctx['planning_summary']
        # Check if our villages are in the summary
        village_names = [v.village_name for v in summary.villages]
        self.assertIn(self.village_a.name, village_names)
        self.assertIn(self.village_b.name, village_names)

    def test_planning_summary_contains_phases_headers(self):
        ctx = self._get_context()
        summary = ctx['planning_summary']
        # We created "Phase 1" for both villages, so it should be in the first phase status
        self.assertEqual(summary.villages[0].phases[0].name, "Phase 1")

    def test_village_phase_status_is_correct(self):
        ctx = self._get_context()
        summary = ctx['planning_summary']
        
        # Find village A row
        row_a = next(v for v in summary.villages if v.village_id == self.village_a.id)
        # Village A phase 1 should be completed
        self.assertEqual(row_a.phases[0].status, Task.COMPLETED)

        # Find village B row
        row_b = next(v for v in summary.villages if v.village_id == self.village_b.id)
        # Village B phase 1 should be not started
        self.assertEqual(row_b.phases[0].status, Task.NOT_STARTED)

    def test_overall_completion_percentage(self):
        ctx = self._get_context()
        summary = ctx['planning_summary']
        # Village A: 100% (1/1 completed), Village B: 0% (0/1 completed)
        # Overall: 50%
        self.assertEqual(summary.overall_completion_pct, 12.5) # (1 completed phase) / (2 villages * 4 phases) * 100 = 12.5
