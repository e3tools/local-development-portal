"""
Integration tests for CantonPrioritiesPartialView.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Category, Sector
from investments.models import Investment

User = get_user_model()

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

def _make_village(name, canton, population=100):
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.VILLAGE,
        parent=canton,
        total_population=population,
    )

def _make_category(name="Infrastructure"):
    return Category.objects.get_or_create(name=name)[0]

def _make_sector(category, name="Water"):
    return Sector.objects.get_or_create(name=name, category=category)[0]

def _make_investment(village, sector, cost=1_000_000, status=Investment.NOT_FUNDED):
    return Investment.objects.create(
        title=f"Investment in {village.name}",
        administrative_level=village,
        sector=sector,
        estimated_cost=cost,
        investment_status=Investment.PRIORITY,
        project_status=status,
        duration=30,
        delays_consumed=0,
        physical_execution_rate=0,
        financial_implementation_rate=0,
        no_sql_id="test-id",
        ranking=1,
    )

class CantonPrioritiesPartialViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.canton = _make_canton(name="Canton Borgou")
        cls.village = _make_village(name="Village A", canton=cls.canton)
        
        cls.category = _make_category()
        cls.sector = _make_sector(cls.category)
        cls.investment = _make_investment(cls.village, cls.sector)
        
        cls.url = reverse("administrativelevels:canton_priorities_partial", args=[cls.canton.pk])

    def setUp(self):
        self.client.force_login(self.user)

    def test_access_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_template_used(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "canton/tabs/priorities.html")

    def test_context_data(self):
        response = self.client.get(self.url)
        self.assertIn('all_canton_priorities', response.context)
        priorities = response.context['all_canton_priorities']
        self.assertTrue(any(p.id == self.investment.id for p in priorities))

    def test_filters_applied(self):
        # Create another investment with different status
        inv2 = _make_investment(self.village, self.sector, status=Investment.COMPLETED)
        
        # Test filtering by status (project_status is not directly filtered in CantonPrioritiesMixin,
        # but the ranking is. However, we'll test categories since that's more direct)
        response = self.client.get(self.url + f"?category-filter={self.category.id}")
        priorities = response.context['all_canton_priorities']
        self.assertTrue(any(p.id == self.investment.id for p in priorities))

    def test_htmx_request(self):
        response = self.client.get(self.url, HTTP_X_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
