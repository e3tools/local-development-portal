"""
test_canton_map_service.py
--------------------------
Unit tests for CantonMapService.
Run with:  python manage.py test administrativelevels.tests.test_canton_map_service
"""

from unittest.mock import MagicMock

from django.test import TestCase

from administrativelevels.services.canton_map_service import (
    CantonMapService,
    PLANNING_COMPLETED,
    NO_PRIORITY_COLOR,
    _CategoryColorRegistry,
)


class SectorColorTests(TestCase):
    """Tests for the helper _CategoryColorRegistry."""

    def test_known_category_returns_stable_colour(self):
        registry = _CategoryColorRegistry()
        color1 = registry.color_for("Education")
        color2 = registry.color_for("EDUCATION ")
        self.assertEqual(color1, color2)
        self.assertIn("#", color1)

    def test_different_categories_return_different_colours(self):
        registry = _CategoryColorRegistry()
        color_edu = registry.color_for("Education")
        color_water = registry.color_for("Water")
        self.assertNotEqual(color_edu, color_water)

    def test_none_category_returns_default(self):
        registry = _CategoryColorRegistry()
        from administrativelevels.services.canton_map_service import _PALETTE
        self.assertEqual(registry.color_for(None), _PALETTE[0])


class CantonMapServiceBoundsTests(TestCase):
    """Tests for the _compute_bounds static method."""

    def test_empty_coords_returns_none(self):
        result = CantonMapService._compute_bounds([])
        self.assertIsNone(result)

    def test_single_coord_returns_padded_box(self):
        result = CantonMapService._compute_bounds([(10.0, 8.0)])
        self.assertIsNotNone(result)
        min_lng, min_lat = result[0]
        max_lng, max_lat = result[1]
        self.assertLess(min_lng, 10.0)
        self.assertGreater(max_lng, 10.0)
        self.assertLess(min_lat, 8.0)
        self.assertGreater(max_lat, 8.0)

    def test_multiple_coords_correct_bounds(self):
        coords = [(10.0, 8.0), (11.0, 9.0), (10.5, 8.5)]
        result = CantonMapService._compute_bounds(coords)
        self.assertAlmostEqual(result[0][0], 10.0 - 0.05, places=5)
        self.assertAlmostEqual(result[1][0], 11.0 + 0.05, places=5)


class CantonMapServicePhaseStatusTests(TestCase):
    """Tests for _phase_status static method."""

    def _make_task(self, status):
        task = MagicMock()
        task.status = status
        return task

    def _make_activity(self, task_statuses):
        activity = MagicMock()
        activity.tasks.all.return_value = [self._make_task(s) for s in task_statuses]
        return activity

    def _make_phase(self, activities_task_statuses):
        phase = MagicMock()
        phase.activities.all.return_value = [
            self._make_activity(ts) for ts in activities_task_statuses
        ]
        return phase

    def test_all_completed_returns_completed(self):
        phase = self._make_phase([["completed", "completed"]])
        self.assertEqual(CantonMapService._phase_status(phase), "completed")

    def test_all_not_started_returns_not_started(self):
        phase = self._make_phase([["not started", "not started"]])
        self.assertEqual(CantonMapService._phase_status(phase), "not_started")

    def test_mixed_returns_in_progress(self):
        phase = self._make_phase([["completed", "not started"]])
        self.assertEqual(CantonMapService._phase_status(phase), "in_progress")

    def test_empty_tasks_returns_not_started(self):
        phase = self._make_phase([[]])
        self.assertEqual(CantonMapService._phase_status(phase), "not_started")


class CantonMapServiceFeatureTests(TestCase):
    """Tests for _build_feature output structure."""

    def _make_investment(self, status, ranking=1, sector_name="Education",
                         category_name="Education", estimated_cost=1000, climate=False):
        inv = MagicMock()
        inv.project_status = status
        inv.ranking = ranking
        inv.title = "Test Investment"
        inv.estimated_cost = estimated_cost
        inv.climate_contribution = climate
        sector = MagicMock()
        sector.name = sector_name
        category = MagicMock()
        category.name = category_name
        sector.category = category
        inv.sector = sector
        return inv

    def _make_village(self, latitude=8.5, longitude=1.5, investments=None, phases=None):
        village = MagicMock(spec=["id", "name", "latitude", "longitude",
                                  "total_population", "investments", "phases"])
        village.id = 1
        village.name = "Test Village"
        village.latitude = latitude
        village.longitude = longitude
        village.total_population = 500
        village.investments.all.return_value = investments or []
        village.phases.all.return_value = phases or []
        return village

    def test_village_without_priority_has_grey_color(self):
        """A village with no unfunded investments should show grey on priorities layer."""
        village = self._make_village()
        canton = MagicMock()
        canton.type = "Canton"
        service = CantonMapService(canton)
        feature = service._build_feature(village)
        self.assertFalse(feature["has_priority"])
        self.assertEqual(feature["priority_color"], NO_PRIORITY_COLOR)

    def test_village_with_priority_has_sector_color(self):
        """A village with an unfunded investment should show category color."""
        from investments.models import Investment
        inv = self._make_investment(Investment.NOT_FUNDED, ranking=1, sector_name="Health", category_name="Health")
        village = self._make_village(investments=[inv])
        canton = MagicMock()
        canton.type = "Canton"
        service = CantonMapService(canton)
        feature = service._build_feature(village)
        self.assertTrue(feature["has_priority"])
        # The color is now dynamic, so we check if it matches the registry
        expected_color = service._color_registry.color_for("Health")
        self.assertEqual(feature["priority_color"], expected_color)

    def test_village_without_coordinates_still_builds_feature(self):
        """Villages without lat/lng should still produce a feature (lat/lng = None)."""
        village = self._make_village(latitude=None, longitude=None)
        canton = MagicMock()
        canton.type = "Canton"
        service = CantonMapService(canton)
        feature = service._build_feature(village)
        self.assertIsNone(feature["latitude"])
        self.assertIsNone(feature["longitude"])

    def test_planning_completed_village(self):
        """A village where all phases are complete should show green."""
        from administrativelevels.models import Task
        task = MagicMock()
        task.status = Task.COMPLETED
        activity = MagicMock()
        activity.tasks.all.return_value = [task]
        phase = MagicMock()
        phase.activities.all.return_value = [activity]
        village = self._make_village(phases=[phase])
        canton = MagicMock()
        canton.type = "Canton"
        service = CantonMapService(canton)
        feature = service._build_feature(village)
        self.assertEqual(feature["planning_status"], "completed")
        self.assertEqual(feature["planning_color"], PLANNING_COMPLETED)
