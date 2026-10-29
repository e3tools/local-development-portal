"""
Access control on the /investments/ AJAX endpoints. InvestmentModelViewSet was
a full ModelViewSet with DRF's default AllowAny: anonymous visitors could list
and delete investments.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Category, Sector
from investments.models import Investment

User = get_user_model()


class InvestmentAjaxPermissionTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.approved = User.objects.create_user(
            username="approved@email.com", email="approved@email.com",
            password="testpass123", is_approved=True,
        )
        cls.not_approved = User.objects.create_user(
            username="pending@email.com", email="pending@email.com",
            password="testpass123", is_approved=False,
        )
        village = AdministrativeLevel.objects.create(
            name="Village P", type=AdministrativeLevel.VILLAGE
        )
        sector = Sector.objects.create(
            name="Water", category=Category.objects.create(name="Infra")
        )
        cls.investment = Investment.objects.create(
            title="Forage", administrative_level=village, sector=sector,
            estimated_cost=1_000_000, duration=30, delays_consumed=0,
            physical_execution_rate=0, financial_implementation_rate=0,
            investment_status=Investment.PRIORITY, no_sql_id="perm-test",
        )
        base = reverse("investments:home_investments") + "ajax/"
        cls.list_url = base + "datatable/?format=datatables"
        cls.detail_url = base + "datatable/%d/" % cls.investment.id
        cls.totals_url = base + "datatable/total-results/"
        cls.results_url = base + "datatable/results/"
        cls.adm_levels_url = base + "adm-levels"
        cls.sectors_url = base + "sectors"
        cls.totals_data = {"all_queryset": "false", "selected_ids": "", "project_id": ""}

    def _read_responses(self):
        return {
            "list": self.client.get(self.list_url).status_code,
            "detail": self.client.get(self.detail_url).status_code,
            "total-results": self.client.post(self.totals_url, self.totals_data).status_code,
            "results": self.client.post(self.results_url, self.totals_data).status_code,
            "adm-levels": self.client.post(self.adm_levels_url, {"value": ""}).status_code,
            "sectors": self.client.post(self.sectors_url, {"value": ""}).status_code,
        }

    def test_anonymous_is_refused_everywhere(self):
        # 401 rather than 403: JWTAuthentication (first backend) sends a
        # WWW-Authenticate challenge. Either way the request is refused.
        for name, status in self._read_responses().items():
            self.assertIn(status, (401, 403), name)

    def test_unapproved_user_is_refused_everywhere(self):
        self.client.force_login(self.not_approved)
        for name, status in self._read_responses().items():
            self.assertEqual(status, 403, name)

    def test_approved_user_can_read(self):
        self.client.force_login(self.approved)
        for name, status in self._read_responses().items():
            self.assertEqual(status, 200, name)

    def test_anonymous_cannot_delete(self):
        self.client.delete(self.detail_url)
        self.assertTrue(Investment.objects.filter(id=self.investment.id).exists())

    def test_writes_are_not_allowed_even_for_approved_users(self):
        self.client.force_login(self.approved)
        self.assertEqual(self.client.delete(self.detail_url).status_code, 405)
        self.assertEqual(
            self.client.put(self.detail_url, {}, content_type="application/json").status_code, 405
        )
        self.assertEqual(
            self.client.patch(self.detail_url, {}, content_type="application/json").status_code, 405
        )
        self.assertEqual(self.client.post(self.list_url, {}).status_code, 405)
        self.assertTrue(Investment.objects.filter(id=self.investment.id).exists())
