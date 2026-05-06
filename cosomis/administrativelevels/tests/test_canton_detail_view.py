"""
Integration tests for CantonDetailView.

Strategy: use Django's TestClient with a real (SQLite) test database.
All objects are created with baker/factory helpers kept inline so this file
is self-contained and easy to read.

Fixtures created per test (unless shared via setUpTestData):
  - One Canton AdministrativeLevel
  - Two Village children under that Canton
  - One Investment (priority) per village
  - One Attachment (photo) per village
  - One User with staff privileges (required by LoginRequiredApproveRequiredMixin)

Run with:
    python manage.py test administrativelevels.tests.test_canton_detail_view
"""

from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Category, Sector
from investments.models import Investment, Attachment

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="officer@email.com", approved=True, **kwargs):
    """Create a minimal user that passes LoginRequiredApproveRequiredMixin."""
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


def _make_investment(village, sector, cost=1_000_000,
                     status=Investment.NOT_FUNDED):
    return Investment.objects.create(
        title=f"Investment in {village.name}",
        administrative_level=village,
        sector=sector,
        estimated_cost=cost,
        real_cost=None,
        start_date=None,
        duration=30,
        delays_consumed=0,
        physical_execution_rate=0,
        financial_implementation_rate=0,
        investment_status=Investment.PRIORITY,
        project_status=status,
        no_sql_id="test-id",
    )


def _make_attachment(village, url="https://s3.example.com/photo.jpg",
                     moment=Attachment.COMMUNITY_PROCESS):
    return Attachment.objects.create(
        adm=village,
        url=url,
        type=Attachment.PHOTO,
        process_moment=moment,
    )


# ---------------------------------------------------------------------------
# Base class — shared setup
# ---------------------------------------------------------------------------

class CantonDetailViewBaseTest(TestCase):
    """
    Creates the minimal object graph needed for all integration tests.
    Uses setUpTestData for objects that are read-only across tests (faster).
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.canton = _make_canton(name="Canton Borgou")

        cls.village_a = _make_village(
            name="Village Alpha",
            canton=cls.canton,
            population=1000, men=450, women=550,
            young=300, elder=100, handicap=40,
            agriculturist=200, pastoralist=80, minorities=60
        )
        cls.village_b = _make_village(
            name="Village Beta",
            canton=cls.canton,
            population=500, men=220, women=280,
            young=150, elder=50, handicap=20,
            agriculturist=100, pastoralist=40, minorities=30
        )

        cls.category = _make_category()
        cls.sector = _make_sector(cls.category)

        cls.url = reverse("administrativelevels:canton_detail", args=[cls.canton.pk])

    def _login(self):
        self.client.force_login(self.user)


# ---------------------------------------------------------------------------
# Test Group 1 — HTTP / access control
# ---------------------------------------------------------------------------

class CantonDetailViewAccessTest(CantonDetailViewBaseTest):

    def test_redirects_anonymous_user_to_login(self):
        """Unauthenticated request must redirect to login, not 200/500."""
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [301, 302])
        self.assertNotEqual(response.status_code, 200)

    def test_authenticated_user_gets_200(self):
        """An approved logged-in user should receive HTTP 200."""
        self._login()
        # Package.objects.get_active_cart creates a Package — mock to avoid side effects
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_canton_detail_template(self):
        """View must render canton/canton_detail.html."""
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(self.url)
        self.assertTemplateUsed(response, "canton/canton_detail.html")

    def test_non_existent_canton_returns_404(self):
        """Requesting a pk that does not exist must return 404."""
        self._login()
        bad_url = reverse("administrativelevels:canton_detail", args=[99999])
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Test Group 2 — Population card
# ---------------------------------------------------------------------------

class CantonDetailViewPopulationContextTest(CantonDetailViewBaseTest):

    def _get_context(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(self.url)
        return response.context

    def test_canton_population_key_exists_in_context(self):
        """Context must include canton_population dict."""
        ctx = self._get_context()
        self.assertIn('canton_population', ctx)

    def test_total_population_is_sum_of_child_villages(self):
        """total must equal village_a.population + village_b.population."""
        ctx = self._get_context()
        expected = self.village_a.total_population + self.village_b.total_population
        self.assertEqual(ctx['canton_population']['total'], expected)

    def test_men_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_men + self.village_b.population_men
        self.assertEqual(ctx['canton_population']['men'], expected)

    def test_women_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_women + self.village_b.population_women
        self.assertEqual(ctx['canton_population']['women'], expected)

    def test_young_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_young + self.village_b.population_young
        self.assertEqual(ctx['canton_population']['young'], expected)

    def test_elder_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_elder + self.village_b.population_elder
        self.assertEqual(ctx['canton_population']['elder'], expected)

    def test_disabilities_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_handicap + self.village_b.population_handicap
        self.assertEqual(ctx['canton_population']['disabilities'], expected)

    def test_ethnic_groups_population_is_aggregated(self):
        ctx = self._get_context()
        expected = self.village_a.population_minorities + self.village_b.population_minorities
        self.assertEqual(ctx['canton_population']['minorities'], expected)

    def test_population_zero_when_no_child_villages(self):
        """An empty canton must return zeros, not None or crash."""
        empty_canton = _make_canton(name="Canton Vide")
        url = reverse("administrativelevels:canton_detail", args=[empty_canton.pk])
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(url)
        ctx = response.context
        self.assertEqual(ctx['canton_population']['total'], 0)
        self.assertEqual(ctx['canton_population']['men'], 0)


# ---------------------------------------------------------------------------
# Test Group 3 — Villages Summary card
# ---------------------------------------------------------------------------

class CantonDetailViewVillagesSummaryContextTest(CantonDetailViewBaseTest):

    def _get_context(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(self.url)
        return response.context

    def test_villages_summary_key_exists_in_context(self):
        """Context must include villages_summary dict."""
        ctx = self._get_context()
        self.assertIn('villages_summary', ctx)

    def test_village_count_is_correct(self):
        """village_count must equal the number of direct child villages."""
        ctx = self._get_context()
        self.assertEqual(ctx['villages_summary']['village_count'], 2)

    def test_priority_count_counts_all_investments(self):
        """priority_count must reflect investments across all child villages."""
        inv_a = _make_investment(self.village_a, self.sector, cost=500_000)
        inv_b = _make_investment(self.village_b, self.sector, cost=750_000)
        ctx = self._get_context()
        self.assertGreaterEqual(ctx['villages_summary']['priority_count'], 2)
        # Cleanup so other tests are not affected (setUpTestData is rolled back
        # automatically, but objects created in test methods are not)
        inv_a.delete()
        inv_b.delete()

    def test_total_estimated_cost_is_sum_of_investments(self):
        """total_estimated_cost must equal sum of all child investment costs."""
        inv_a = _make_investment(self.village_a, self.sector, cost=1_000_000)
        inv_b = _make_investment(self.village_b, self.sector, cost=2_000_000)
        ctx = self._get_context()
        self.assertEqual(ctx['villages_summary']['total_estimated_cost'], 3_000_000)
        inv_a.delete()
        inv_b.delete()

    def test_villages_summary_zero_when_no_investments(self):
        """With no investments, cost and count must be 0, not None."""
        ctx = self._get_context()
        self.assertEqual(ctx['villages_summary']['total_estimated_cost'], 0)
        self.assertEqual(ctx['villages_summary']['priority_count'], 0)

    def test_villages_summary_required_keys_present(self):
        """All four required keys must be present in villages_summary."""
        ctx = self._get_context()
        required_keys = {'village_count', 'cvd_count', 'priority_count', 'total_estimated_cost'}
        self.assertTrue(
            required_keys.issubset(ctx['villages_summary'].keys()),
            f"Missing keys: {required_keys - ctx['villages_summary'].keys()}"
        )


# ---------------------------------------------------------------------------
# Test Group 4 — Carousel images
# ---------------------------------------------------------------------------

class CantonDetailViewCarouselContextTest(CantonDetailViewBaseTest):

    def _get_context(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            response = self.client.get(self.url)
        return response.context

    def test_images_data_key_exists_in_context(self):
        ctx = self._get_context()
        self.assertIn('images_data', ctx)

    def test_no_images_returns_exists_at_least_image_false(self):
        """When no attachments exist, exists_at_least_image must be False."""
        ctx = self._get_context()
        self.assertFalse(ctx['images_data']['exists_at_least_image'])
        self.assertIsNone(ctx['images_data']['first_image'])

    def test_attachment_from_child_village_appears_in_carousel(self):
        """A photo attached to a child village must be included."""
        att = _make_attachment(self.village_a)
        ctx = self._get_context()
        self.assertTrue(ctx['images_data']['exists_at_least_image'])
        image_ids = [img.id for img in ctx['images_data']['images']]
        self.assertIn(att.id, image_ids)
        att.delete()

    def test_completed_infrastructure_image_takes_priority(self):
        """COMPLETED images must appear before COMMUNITY images."""
        community_att = _make_attachment(
            self.village_a,
            url="https://s3.example.com/community.jpg",
            moment=Attachment.COMMUNITY_PROCESS
        )
        completed_att = _make_attachment(
            self.village_b,
            url="https://s3.example.com/completed.jpg",
            moment=Attachment.COMPLETED_INFRASTRUCTURE
        )
        ctx = self._get_context()
        images = ctx['images_data']['images']
        image_ids = [img.id for img in images]
        # completed must come first
        self.assertLess(
            image_ids.index(completed_att.id),
            image_ids.index(community_att.id),
            "COMPLETED_INFRASTRUCTURE image should appear before COMMUNITY_PROCESS"
        )
        community_att.delete()
        completed_att.delete()

    def test_carousel_capped_at_max_five_images(self):
        """Carousel must never return more than 5 images."""
        attachments = [
            _make_attachment(
                self.village_a,
                url=f"https://s3.example.com/photo_{i}.jpg"
            )
            for i in range(8)
        ]
        ctx = self._get_context()
        self.assertLessEqual(len(ctx['images_data']['images']), 5)
        for att in attachments:
            att.delete()


# ---------------------------------------------------------------------------
# Test Group 5 — Template rendering (smoke tests)
# ---------------------------------------------------------------------------

class CantonDetailViewTemplateRenderingTest(CantonDetailViewBaseTest):

    def _get_response(self):
        self._login()
        with patch('investments.models.PackageQuerySet.get_active_cart') as mock_cart:
            mock_cart.return_value = MagicMock(
                funded_investments=MagicMock(all=lambda: [])
            )
            return self.client.get(self.url)

    def test_population_total_rendered_in_html(self):
        """The aggregated total population must appear in the rendered HTML."""
        response = self._get_response()
        total = self.village_a.total_population + self.village_b.total_population
        # We check both formatted and unformatted just in case,
        # but intcomma is used in the template.
        self.assertTrue(str(total).replace(',', '') in response.content.decode().replace(
            ',', '').replace('\xa0', '').replace(' ', ''))

    def test_village_count_rendered_in_html(self):
        """The Villages summary card must show the village count."""
        response = self._get_response()
        self.assertContains(response, '2')  # 2 child villages

    def test_default_image_shown_when_no_attachments(self):
        """When no images exist, the default village-image.jpg src must appear."""
        response = self._get_response()
        self.assertContains(response, 'village-image.jpg')

    def test_carousel_shown_when_attachment_exists(self):
        """When images exist, the carousel div must appear and default must not."""
        att = _make_attachment(
            self.village_a,
            url="https://s3.example.com/photo.jpg"
        )
        response = self._get_response()
        self.assertContains(response, 'cantonCarousel')
        self.assertNotContains(response, 'village-image.jpg')
        att.delete()

    def test_page_title_contains_canton_name(self):
        """The page title must include the canton's name."""
        response = self._get_response()
        self.assertContains(response, self.canton.name)
