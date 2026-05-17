from unittest.mock import MagicMock

from django.test import TestCase

from administrativelevels.models import AdministrativeLevel
from administrativelevels.services.canton_planning_service import (
    CantonPlanningService,
    CantonPlanningRepository,
    CantonPlanningSummary,
    VillagePlanningRow,
    PhaseStatus,
    TOTAL_PHASES_PER_VILLAGE,
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
)


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def _make_canton(pk=1, name="Test Canton"):
    c = MagicMock(spec=AdministrativeLevel)
    c.pk = pk
    c.name = name
    c.type = AdministrativeLevel.CANTON
    c.is_canton.return_value = True
    return c


def _make_village(pk, name):
    v = MagicMock(spec=AdministrativeLevel)
    v.pk = pk
    v.name = name
    v.type = AdministrativeLevel.VILLAGE
    v.is_canton.return_value = False
    return v


def _make_phase(order, status, name=None):
    phase = MagicMock()
    phase.order = order
    phase.name = name or f"Phase {order}"
    phase.get_status.return_value = status
    return phase


def _make_service(canton, villages, phases_by_village):
    """
    Factory: builds a CantonPlanningService with a mocked repository.
    phases_by_village: list of lists, in same order as villages.
    """
    mock_repo = MagicMock(spec=CantonPlanningRepository)
    mock_repo.get_villages_for_canton.return_value = villages
    mock_repo.get_phases_for_village.side_effect = phases_by_village
    return CantonPlanningService(canton, repository=mock_repo)


# ──────────────────────────────────────────────────────────
# PhaseStatus
# ──────────────────────────────────────────────────────────

class TestPhaseStatus(TestCase):

    def test_dot_color_completed(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_COMPLETED).dot_color, "#28a745")

    def test_dot_color_in_progress(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_IN_PROGRESS).dot_color, "#ffc107")

    def test_dot_color_not_started(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_NOT_STARTED).dot_color, "#6c757d")

    def test_dot_color_unknown_falls_back(self):
        self.assertEqual(PhaseStatus(1, "P", "???").dot_color, "#dee2e6")

    def test_css_class_completed(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_COMPLETED).css_class, "completed")

    def test_css_class_in_progress(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_IN_PROGRESS).css_class, "in-progress")

    def test_css_class_not_started(self):
        self.assertEqual(PhaseStatus(1, "P", STATUS_NOT_STARTED).css_class, "not-started")


# ──────────────────────────────────────────────────────────
# VillagePlanningRow
# ──────────────────────────────────────────────────────────

class TestVillagePlanningRow(TestCase):

    def _row(self, c, ip, ns, pc=0):
        row = VillagePlanningRow(1, "V", completed_phases=c, in_progress_phases=ip, not_started_phases=ns, priorities_count=pc)
        # We must provide phases because percentage calculations now depend on len(self.phases)
        row.phases = [PhaseStatus(i, "P", STATUS_COMPLETED) for i in range(c)] + \
                     [PhaseStatus(i, "P", STATUS_IN_PROGRESS) for i in range(ip)] + \
                     [PhaseStatus(i, "P", STATUS_NOT_STARTED) for i in range(ns)]
        return row

    def test_percentages_sum_to_100_when_full(self):
        row = self._row(2, 1, 1)
        self.assertEqual(row.completed_pct + row.in_progress_pct + row.not_started_pct, 100)

    def test_overall_status_completed(self):
        self.assertEqual(self._row(4, 0, 0).overall_status, STATUS_COMPLETED)

    def test_overall_status_in_progress_mixed(self):
        self.assertEqual(self._row(2, 1, 1).overall_status, STATUS_IN_PROGRESS)

    def test_overall_status_in_progress_only_some_completed(self):
        self.assertEqual(self._row(1, 0, 3).overall_status, STATUS_IN_PROGRESS)

    def test_overall_status_not_started(self):
        self.assertEqual(self._row(0, 0, 4).overall_status, STATUS_NOT_STARTED)


# ──────────────────────────────────────────────────────────
# CantonPlanningSummary
# ──────────────────────────────────────────────────────────

class TestCantonPlanningSummary(TestCase):

    def _summary(self, village_count, total_completed_phases, total_phases_per_village=4):
        villages = []
        for i in range(village_count):
            # Distribute completed phases among villages for testing
            # This is a bit arbitrary but needed since overall_completion_pct uses v.phases
            v_completed = total_completed_phases // village_count
            if i < total_completed_phases % village_count:
                v_completed += 1
            
            row = VillagePlanningRow(i, f"V{i}", completed_phases=v_completed, 
                                     in_progress_phases=0, 
                                     not_started_phases=total_phases_per_village - v_completed)
            row.phases = [PhaseStatus(j, "P", STATUS_COMPLETED) for j in range(total_phases_per_village)]
            villages.append(row)

        return CantonPlanningSummary(
            canton_id=1, canton_name="C",
            village_count=village_count,
            completed_villages=0, in_progress_villages=0, not_started_villages=0,
            total_completed_phases=total_completed_phases,
            villages=villages
        )

    def test_100_percent(self):
        self.assertEqual(self._summary(5, 20).overall_completion_pct, 100.0)

    def test_50_percent(self):
        self.assertEqual(self._summary(4, 8).overall_completion_pct, 50.0)

    def test_zero_villages_returns_zero(self):
        self.assertEqual(self._summary(0, 0).overall_completion_pct, 0.0)

    def test_rounds_to_one_decimal(self):
        # 3 / (4 * 4) × 100 = 18.75 → 18.8
        self.assertEqual(self._summary(4, 3).overall_completion_pct, 18.8)


# ──────────────────────────────────────────────────────────
# CantonPlanningService — constructor guard
# ──────────────────────────────────────────────────────────

class TestCantonPlanningServiceGuard(TestCase):

    def test_raises_if_not_canton(self):
        not_a_canton = _make_village(pk=1, name="Village")
        not_a_canton.type = AdministrativeLevel.VILLAGE
        with self.assertRaises(AssertionError):
            CantonPlanningService(not_a_canton)


# ──────────────────────────────────────────────────────────
# CantonPlanningService — get_summary()
# ──────────────────────────────────────────────────────────

class TestCantonPlanningServiceGetSummary(TestCase):

    def test_empty_canton(self):
        canton = _make_canton()
        service = _make_service(canton, villages=[], phases_by_village=[])
        summary = service.get_summary()

        self.assertEqual(summary.village_count, 0)
        self.assertEqual(summary.overall_completion_pct, 0.0)
        self.assertEqual(summary.villages, [])

    def test_one_fully_completed_village(self):
        canton = _make_canton()
        village = _make_village(pk=1, name="AlphaVillage")
        phases = [_make_phase(i, STATUS_COMPLETED) for i in range(1, 5)]

        service = _make_service(canton, [village], [phases])
        summary = service.get_summary()

        self.assertEqual(summary.village_count, 1)
        self.assertEqual(summary.completed_villages, 1)
        self.assertEqual(summary.in_progress_villages, 0)
        self.assertEqual(summary.not_started_villages, 0)
        self.assertEqual(summary.total_completed_phases, 4)
        self.assertEqual(summary.overall_completion_pct, 100.0)

    def test_mixed_three_villages(self):
        """
        Village A: 4 completed  → completed
        Village B: 2 completed, 1 in-progress, 1 not-started → in-progress
        Village C: no phases in DB → not-started
        Expected: total_completed_phases=6, overall=6/8*100=75%
        (Note: Village C has 0 phases, so it doesn't contribute to total_existing_phases)
        """
        canton = _make_canton()
        a = _make_village(pk=1, name="A")
        b = _make_village(pk=2, name="B")
        c = _make_village(pk=3, name="C")

        phases_a = [_make_phase(i, STATUS_COMPLETED) for i in range(1, 5)]
        phases_b = [
            _make_phase(1, STATUS_COMPLETED),
            _make_phase(2, STATUS_COMPLETED),
            _make_phase(3, STATUS_IN_PROGRESS),
            _make_phase(4, STATUS_NOT_STARTED),
        ]
        phases_c = []

        service = _make_service(canton, [a, b, c], [phases_a, phases_b, phases_c])
        summary = service.get_summary()

        self.assertEqual(summary.village_count, 3)
        self.assertEqual(summary.completed_villages, 1)
        self.assertEqual(summary.in_progress_villages, 1)
        self.assertEqual(summary.not_started_villages, 1)
        self.assertEqual(summary.total_completed_phases, 6)
        # Total phases = 4 (A) + 4 (B) + 0 (C) = 8. 6/8 = 75%
        self.assertEqual(summary.overall_completion_pct, 75.0)

    def test_variable_phases(self):
        """Even if only 2 phases exist in DB, we only show those 2."""
        canton = _make_canton()
        village = _make_village(pk=1, name="V")
        phases = [_make_phase(1, STATUS_COMPLETED), _make_phase(2, STATUS_IN_PROGRESS)]

        service = _make_service(canton, [village], [phases])
        summary = service.get_summary()
        row = summary.villages[0]

        self.assertEqual(len(row.phases), 2)
        self.assertEqual(row.phases[0].status, STATUS_COMPLETED)
        self.assertEqual(row.phases[1].status, STATUS_IN_PROGRESS)

    def test_village_row_ids_and_names_match(self):
        canton = _make_canton()
        village = _make_village(pk=42, name="Bêta-Village")

        service = _make_service(canton, [village], [[]])
        summary = service.get_summary()

        self.assertEqual(summary.villages[0].village_id, 42)
        self.assertEqual(summary.villages[0].village_name, "Bêta-Village")

    def test_canton_name_propagated(self):
        canton = _make_canton(pk=7, name="Canton Kara")
        service = _make_service(canton, [], [])
        summary = service.get_summary()
        self.assertEqual(summary.canton_name, "Canton Kara")
        self.assertEqual(summary.canton_id, 7)
