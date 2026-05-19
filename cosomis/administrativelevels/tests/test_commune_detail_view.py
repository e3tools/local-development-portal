"""
Integration tests for CommuneDetailView.
"""

from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.db.models import Q

from administrativelevels.models import AdministrativeLevel, Category, Sector, Task, Activity, Phase
from investments.models import Investment, Attachment, Package

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="officer_commune@email.com", approved=True, **kwargs):
    """Create a minimal user that passes LoginRequiredApproveRequiredMixin."""
    user = User.objects.create_user(
        username=username,
        email=username,
        password="testpass123",
        is_approved=approved,
        **kwargs
    )
    return user


def _make_adm(name, adm_type, parent=None, **kwargs):
    return AdministrativeLevel.objects.create(
        name=name,
        type=adm_type,
        parent=parent,
        **kwargs
    )


def _make_village(name, canton, population=100, men=40, women=60,
                  young=20, elder=10, handicap=5,
                  agriculturist=30, pastoralist=15, minorities=10):
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.VILLAGE,
        parent=canton,
        total_population=population,
        population_men=men,
        population_women=women,
        population_young=young,
        population_elder=elder,
        population_handicap=handicap,
        population_agriculturist=agriculturist,
        population_pastoralist=pastoralist,
        population_minorities=minorities,
    )


def _make_category(name="Infrastructure"):
    return Category.objects.get_or_create(name=name)[0]


def _make_sector(category, name="Water"):
    return Sector.objects.get_or_create(name=name, category=category)[0]


def _make_investment(adm, sector, cost=1_000_000,
                     status=Investment.NOT_FUNDED):
    return Investment.objects.create(
        title=f"Investment in {adm.name}",
        administrative_level=adm,
        sector=sector,
        estimated_cost=cost,
        duration=30,
        delays_consumed=0,
        physical_execution_rate=0,
        financial_implementation_rate=0,
        investment_status=Investment.PRIORITY,
        project_status=status,
        no_sql_id=f"test-id-{adm.id}",
    )


def _make_attachment(adm, url="https://s3.example.com/photo.jpg",
                     moment=Attachment.COMMUNITY_PROCESS):
    return Attachment.objects.create(
        adm=adm,
        url=url,
        type=Attachment.PHOTO,
        process_moment=moment,
    )


# ---------------------------------------------------------------------------
# Base class — shared setup
# ---------------------------------------------------------------------------

class CommuneDetailViewBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.commune = _make_adm("Commune A", AdministrativeLevel.COMMUNE)
        cls.canton = _make_adm("Canton A1", AdministrativeLevel.CANTON, parent=cls.commune)
        
        cls.village_1 = _make_village(
            "Village 1", cls.canton, 
            population=1000, men=500, women=500,
            young=400, elder=100, handicap=50,
            agriculturist=300, pastoralist=100, minorities=50
        )
        cls.village_2 = _make_village(
            "Village 2", cls.canton,
            population=500, men=250, women=250,
            young=200, elder=50, handicap=25,
            agriculturist=150, pastoralist=50, minorities=25
        )

        cls.category = _make_category()
        cls.sector = _make_sector(cls.category)

        cls.url = reverse("administrativelevels:commune_detail", args=[cls.commune.pk])

    def _login(self):
        self.client.force_login(self.user)


# ---------------------------------------------------------------------------
# Test Group 1 — Access Control
# ---------------------------------------------------------------------------

class CommuneDetailViewAccessTest(CommuneDetailViewBaseTest):
    def test_redirects_anonymous(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_200(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "commune/commune_detail.html")


# ---------------------------------------------------------------------------
# Test Group 2 — Population Context
# ---------------------------------------------------------------------------

class CommuneDetailViewPopulationTest(CommuneDetailViewBaseTest):
    def test_population_aggregation(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)
        
        pop = response.context['population']
        self.assertEqual(pop['total'], 1500)
        self.assertEqual(pop['men'], 750)
        self.assertEqual(pop['women'], 750)
        self.assertEqual(pop['village_count'], 2)
        self.assertEqual(pop['canton_count'], 1)


# ---------------------------------------------------------------------------
# Test Group 3 — Carousel Images
# ---------------------------------------------------------------------------

class CommuneDetailViewCarouselTest(CommuneDetailViewBaseTest):
    def test_images_from_descendants(self):
        # Image in village (grandchild)
        att_v = _make_attachment(self.village_1, url="v.jpg", moment=Attachment.COMPLETED_INFRASTRUCTURE)
        # Image in canton (child)
        att_c = _make_attachment(self.canton, url="c.jpg", moment=Attachment.COMMUNITY_PROCESS)
        
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)
        
        images = response.context['images_data']['images']
        image_urls = [img.url for img in images]
        self.assertIn("v.jpg", image_urls)
        self.assertIn("c.jpg", image_urls)
        # COMPLETED should be first
        self.assertEqual(images[0].url, "v.jpg")


# ---------------------------------------------------------------------------
# Test Group 4 — HTMX Cart
# ---------------------------------------------------------------------------

class CommuneDetailViewCartTest(CommuneDetailViewBaseTest):
    def test_toggle_cart_item(self):
        inv = _make_investment(self.village_1, self.sector)
        self._login()
        
        # Add
        self.client.post(self.url, {'cart-toggle': inv.id})
        package = Package.objects.get_active_cart(user=self.user)
        self.assertTrue(package.funded_investments.filter(id=inv.id).exists())
        
        # Remove
        self.client.post(self.url, {'cart-toggle': inv.id})
        self.assertFalse(package.funded_investments.filter(id=inv.id).exists())

    def test_toggle_cart_htmx(self):
        inv = _make_investment(self.village_1, self.sector)
        self._login()
        response = self.client.post(self.url, {'cart-toggle': inv.id}, HTTP_X_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        package = Package.objects.get_active_cart(user=self.user)
        self.assertTrue(package.funded_investments.filter(id=inv.id).exists())


# ---------------------------------------------------------------------------
# Test Group 5 — Priorities and Annotations
# ---------------------------------------------------------------------------

class CommuneDetailViewPrioritiesTest(CommuneDetailViewBaseTest):
    def test_priorities_in_context(self):
        inv1 = _make_investment(self.village_1, self.sector, cost=1000)
        inv2 = _make_investment(self.village_2, self.sector, cost=2000)
        
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)
        
        # Priorities context is built by CommunePrioritiesMixin
        # The key used in _build_priorities_context is 'investments'
        self.assertIn('investments', response.context)
        
        # Check if investments are included
        investments_qs = response.context['investments']
        p_ids = [p.id for p in investments_qs]
        self.assertIn(inv1.id, p_ids)
        self.assertIn(inv2.id, p_ids)
        
# ---------------------------------------------------------------------------
# Test Group 6 — Per Capita Annotations
# ---------------------------------------------------------------------------

class CommuneDetailViewPerCapitaTest(CommuneDetailViewBaseTest):
    def test_per_capita_calculations(self):
        # Village 1: pop 1000
        # Investment 1: funded, cost 10000 -> per_capita_invested = 10000/1000 = 10
        # Investment 2: not funded, cost 5000 -> total_estimated_cost = 15000 -> per_capita_required = 15000/1000 = 15
        _make_investment(self.village_1, self.sector, cost=10000, status=Investment.FUNDED)
        _make_investment(self.village_1, self.sector, cost=5000, status=Investment.NOT_FUNDED)

        # Village 2: pop 500
        # Investment 3: funded, cost 5000 -> per_capita_invested = 5000/500 = 10
        # total_estimated_cost = 5000 -> per_capita_required = 5000/500 = 10
        _make_investment(self.village_2, self.sector, cost=5000, status=Investment.FUNDED)

        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)

        villages = response.context['villages']
        v1_data = next(v for v in villages if v.id == self.village_1.id)
        v2_data = next(v for v in villages if v.id == self.village_2.id)

        self.assertEqual(v1_data.per_capita_invested, 10)
        self.assertEqual(v1_data.per_capita_required, 15)
        self.assertEqual(v2_data.per_capita_invested, 10)
        self.assertEqual(v2_data.per_capita_required, 10)

    def test_per_capita_zero_population(self):
        # Village with 0 population
        village_zero = _make_village("Village Zero", self.canton, population=0)
        _make_investment(village_zero, self.sector, cost=1000, status=Investment.FUNDED)

        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(funded_investments=MagicMock(all=lambda: []))
            response = self.client.get(self.url)

        villages = response.context['villages']
        v_zero_data = next(v for v in villages if v.id == village_zero.id)

        self.assertEqual(v_zero_data.per_capita_invested, 0)
        self.assertEqual(v_zero_data.per_capita_required, 0)
