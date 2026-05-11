"""
Integration tests for CantonMapView.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Sector, Category
from investments.models import Investment

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email="officer@email.com", approved=True, **kwargs):
    user = User.objects.create_user(
        email=email,
        password="testpass123",
        is_approved=approved,
        is_active=True,
        **kwargs
    )
    return user


def _make_canton(name="Canton Test", **kwargs):
    # Ensure hierarchy for some models that might require it
    country = AdministrativeLevel.objects.create(name="Country",
                                                 type=AdministrativeLevel.REGION)  # Using REGION as proxy for top level if COUNTRY is missing
    region = AdministrativeLevel.objects.create(name="Region", type=AdministrativeLevel.REGION, parent=country)
    commune = AdministrativeLevel.objects.create(name="Commune", type=AdministrativeLevel.COMMUNE, parent=region)
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.CANTON,
        parent=commune,
        **kwargs
    )


def _make_village(name, canton, latitude=None, longitude=None):
    return AdministrativeLevel.objects.create(
        name=name,
        type=AdministrativeLevel.VILLAGE,
        parent=canton,
        latitude=latitude,
        longitude=longitude
    )


def _make_investment(village, title, status=Investment.NOT_FUNDED, ranking=1, sector=None):
    return Investment.objects.create(
        title=title,
        administrative_level=village,
        project_status=status,
        ranking=ranking,
        sector=sector,
        estimated_cost=1000,
        duration=10,
        delays_consumed=0,
        physical_execution_rate=0,
        financial_implementation_rate=0,
        no_sql_id=f"inv_{village.pk}_{ranking}"
    )


# ---------------------------------------------------------------------------
# Base class — shared setup
# ---------------------------------------------------------------------------

class CantonMapViewBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.canton = _make_canton(name="Canton Map Test")

        cls.category = Category.objects.create(name="Health")
        cls.sector = Sector.objects.create(name="Hospital", category=cls.category)

        # Village with coordinates
        cls.village_coords = _make_village(
            name="Village With Coords",
            canton=cls.canton,
            latitude=1.23,
            longitude=4.56
        )
        _make_investment(cls.village_coords, "Clinic", status=Investment.NOT_FUNDED, sector=cls.sector)

        # Village without coordinates
        cls.village_no_coords = _make_village(
            name="Village No Coords",
            canton=cls.canton
        )
        _make_investment(cls.village_no_coords, "Well", status=Investment.FUNDED, sector=cls.sector)

        cls.url = reverse("administrativelevels:canton_map", args=[cls.canton.pk])

    def _login(self):
        self.client.login(email=self.user.email, password="testpass123")


# ---------------------------------------------------------------------------
# Test Group 1 — HTTP / access control
# ---------------------------------------------------------------------------

class CantonMapViewAccessTest(CantonMapViewBaseTest):

    def test_redirects_anonymous_user_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_gets_200(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_uses_correct_template(self):
        self._login()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "canton/tabs/map_tab.html")

    def test_non_existent_canton_returns_404(self):
        self._login()
        bad_url = reverse("administrativelevels:canton_map", args=[99999])
        response = self.client.get(bad_url)
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# Test Group 2 — Map Context
# ---------------------------------------------------------------------------

class CantonMapViewContextTest(CantonMapViewBaseTest):

    def _get_context(self):
        self._login()
        response = self.client.get(self.url)
        return response.context

    def test_context_contains_expected_keys(self):
        ctx = self._get_context()
        self.assertIn('mapbox_access_token', ctx)
        self.assertIn('villages_map_data_json', ctx)

    def test_villages_map_data_is_valid_json(self):
        ctx = self._get_context()
        data = json.loads(ctx['villages_map_data_json'])
        self.assertIn('features', data)
        self.assertIn('subprojects', data)
        self.assertIn('bounds', data)
        self.assertIn('category_legend', data)

    def test_features_contain_village_data(self):
        ctx = self._get_context()
        data = json.loads(ctx['villages_map_data_json'])
        features = data['features']

        village_names = [f['name'] for f in features]
        self.assertIn(self.village_coords.name, village_names)
        self.assertIn(self.village_no_coords.name, village_names)

        # Village with coords should have them in feature
        v_coords_feat = next(f for f in features if f['name'] == self.village_coords.name)
        self.assertEqual(float(v_coords_feat['longitude']), 4.56)
        self.assertEqual(float(v_coords_feat['latitude']), 1.23)

    def test_subprojects_contains_active_investments(self):
        ctx = self._get_context()
        data = json.loads(ctx['villages_map_data_json'])
        subprojects = data['subprojects']

        # Village No Coords has a Funded investment (Well)
        sub_titles = [s['title'] for s in subprojects]
        self.assertIn("Well", sub_titles)

        # Well subproject should have Village No Coords info even if no coords
        well_sub = next(s for s in subprojects if s['title'] == "Well")
        self.assertEqual(well_sub['village_name'], self.village_no_coords.name)

    def test_bounds_are_calculated_from_coords(self):
        ctx = self._get_context()
        data = json.loads(ctx['villages_map_data_json'])
        bounds = data['bounds']

        # Only one village has coords [4.56, 1.23]
        # Padding is 0.05
        # Bounds should be [[4.56 - 0.05, 1.23 - 0.05], [4.56 + 0.05, 1.23 + 0.05]]
        expected = [[4.51, 1.18], [4.61, 1.28]]

        # Use almost equal for floats or round them
        self.assertAlmostEqual(bounds[0][0], 4.51)
        self.assertAlmostEqual(bounds[0][1], 1.18)
        self.assertAlmostEqual(bounds[1][0], 4.61)
        self.assertAlmostEqual(bounds[1][1], 1.28)
