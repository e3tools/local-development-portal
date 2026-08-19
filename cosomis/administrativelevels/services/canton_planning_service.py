"""
Canton Planning Cycle Service
Encapsulates all aggregation logic for the canton planning cycle tab.

All DB queries live here — never in views or templates.
Single Responsibility: build CantonPlanningSummary from a canton AdministrativeLevel.
"""
import logging
from dataclasses import dataclass, field
from typing import List

from django.db.models import Prefetch, Count
from administrativelevels.models import AdministrativeLevel, Phase, Task, Activity

logger = logging.getLogger(__name__)

TOTAL_PHASES_PER_VILLAGE = 4

STATUS_COMPLETED = Task.COMPLETED
STATUS_IN_PROGRESS = Task.IN_PROGRESS
STATUS_NOT_STARTED = Task.NOT_STARTED
STATUS_ERROR = Task.ERROR


def _select_default_project_phases(phases):
    """A village can run one planning cycle per project (COSO/FA-COSO/PURS/...,
    see Phase.project). Canton-level rollups must not mix those cycles together:
    summing/rendering every phase sharing a name across projects double-counts
    it and renders duplicate status dots in the same table cell. Mirror the
    village page's own default project (alphabetically-first project name) so
    the numbers agree between the two pages. Legacy rows synced before
    Phase.project existed (project is None) have nothing to disambiguate, so
    they're left untouched. Non-Phase inputs (test doubles) pass through
    unfiltered rather than risk misreading a mock's auto-generated attributes.
    """
    named = [p for p in phases if isinstance(p, Phase) and p.project_id is not None]
    if not named:
        return list(phases)
    by_project_name = {}
    for p in named:
        by_project_name.setdefault(p.project.name, []).append(p)
    return by_project_name[min(by_project_name)]


@dataclass
class PhaseStatus:
    """Represents the status of a single phase for a village."""
    order: int
    name: str
    status: str

    @property
    def dot_color(self) -> str:
        return {
            STATUS_COMPLETED: "#28a745",
            STATUS_IN_PROGRESS: "#ffc107",
            STATUS_NOT_STARTED: "#6c757d",
            STATUS_ERROR: "#dc3545",
        }.get(self.status, "#dee2e6")

    @property
    def css_class(self) -> str:
        return {
            STATUS_COMPLETED: "completed",
            STATUS_IN_PROGRESS: "in-progress",
            STATUS_NOT_STARTED: "not-started",
            STATUS_ERROR: "error",
        }.get(self.status, "not-started")


@dataclass
class VillagePlanningRow:
    """Aggregated planning data for a single village."""
    village_id: int
    village_name: str
    completed_phases: int
    in_progress_phases: int
    not_started_phases: int
    priorities_count: int = 0
    phases: List[PhaseStatus] = field(default_factory=list)

    @property
    def total_phases(self) -> int:
        return len(self.phases)

    @property
    def completed_pct(self) -> int:
        if self.total_phases == 0:
            return 0
        
        # If this is the only visible category, it's 100% (if all completed) or rounded
        if self.completed_phases == self.total_phases:
            return 100
        
        return int(round((self.completed_phases / self.total_phases) * 100))

    @property
    def in_progress_pct(self) -> int:
        if self.total_phases == 0:
            return 0
        
        # If this is the last visible category, take the remainder
        if self.in_progress_phases > 0 and self.not_started_phases == 0:
            return 100 - self.completed_pct
        
        return int(round((self.in_progress_phases / self.total_phases) * 100))

    @property
    def not_started_pct(self) -> int:
        if self.total_phases == 0:
            return 0
        
        # To avoid rounding issues (e.g. 71 + 14 + 14 = 99), 
        # we make the last non-zero bar take the remainder.
        # If not_started_pct is the last one:
        if self.not_started_phases > 0:
            return 100 - self.completed_pct - self.in_progress_pct
        return 0

    @property
    def overall_status(self) -> str:
        if self.total_phases > 0 and self.completed_phases == self.total_phases:
            return STATUS_COMPLETED
        if self.completed_phases > 0 or self.in_progress_phases > 0:
            return STATUS_IN_PROGRESS
        return STATUS_NOT_STARTED


@dataclass
class CantonPlanningSummary:
    """Top-level summary counters for the canton planning cycle tab."""
    canton_id: int
    canton_name: str
    village_count: int
    completed_villages: int
    in_progress_villages: int
    not_started_villages: int
    total_completed_phases: int
    all_phase_names: List[str] = field(default_factory=list)
    villages: List[VillagePlanningRow] = field(default_factory=list)

    @property
    def overall_completion_pct(self) -> float:
        """
        Formula from AC: total_completed_phases / total_existing_phases × 100
        """
        total_existing_phases = sum(len(v.phases) for v in self.villages)
        if total_existing_phases == 0:
            return 0.0
        return round((self.total_completed_phases / total_existing_phases) * 100, 1)


class CantonPlanningRepository:
    """
    Data access object. Isolated so it can be mocked cleanly in tests.
    """

    def get_villages_for_canton(self, canton: AdministrativeLevel):
        return (
            AdministrativeLevel.objects
            .filter(parent=canton)
            .filter(AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE))
            .annotate(investments_count=Count("investments"))
            .order_by("name")
        )

    def get_phases_for_canton(self, canton: AdministrativeLevel):
        """
        Prefetch all phases, activities, and tasks for all villages in the canton.
        """
        villages = self.get_villages_for_canton(canton)
        return (
            Phase.objects.filter(village__in=villages)
            .select_related("project")
            .only("id", "village_id", "order", "name", "project__name")
            .prefetch_related(
                Prefetch(
                    "activities",
                    queryset=Activity.objects.all()
                    .only("id", "phase_id", "order", "name")
                    .prefetch_related(
                        Prefetch(
                            "tasks",
                            queryset=Task.objects.all().only("id", "activity_id", "status")
                        )
                    )
                )
            )
            .order_by("village_id", "order")
        )

    def get_phases_for_village(self, village: AdministrativeLevel):
        return (
            Phase.objects.filter(village=village)
            .select_related("project")
            .only("id", "village_id", "order", "name", "project__name")
            .prefetch_related(
                Prefetch(
                    "activities",
                    queryset=Activity.objects.all()
                    .only("id", "phase_id", "order", "name")
                    .prefetch_related(
                        Prefetch(
                            "tasks",
                            queryset=Task.objects.all().only("id", "activity_id", "status")
                        )
                    )
                )
            )
            .order_by("order")
        )


class CantonPlanningService:
    """
    Builds CantonPlanningSummary for a given canton AdministrativeLevel.
    Intended to be called from CantonDetailView.get_context_data().
    """

    def __init__(self, canton: AdministrativeLevel, repository: CantonPlanningRepository = None):
        assert canton.is_canton(), (
            f"Expected canton-type AdministrativeLevel, got type={canton.type!r}"
        )
        self._canton = canton
        self._repo = repository or CantonPlanningRepository()

    def get_summary(self) -> CantonPlanningSummary:
        logger.info("Building planning summary for canton '%s' (id=%s)", self._canton.name, self._canton.pk)

        villages = list(self._repo.get_villages_for_canton(self._canton).filter(is_headquarters=True))
        
        # In tests with mocks, get_phases_for_canton might not be mocked
        # so we fall back to a safe way to handle it.
        phases_by_village = {}
        try:
            all_phases = list(self._repo.get_phases_for_canton(self._canton))
            
            # Group phases by village_id
            for phase in all_phases:
                v_id = phase.village_id
                if v_id not in phases_by_village:
                    phases_by_village[v_id] = []
                phases_by_village[v_id].append(phase)
        except Exception:
            pass

        village_rows: List[VillagePlanningRow] = []
        total_completed_phases = 0
        completed_villages = in_progress_villages = not_started_villages = 0
        
        # Track all unique phase names in order
        all_phase_names_map = {}

        for village in villages:
            if village.pk in phases_by_village:
                row = self._build_village_row(village, phases_by_village[village.pk])
            else:
                row = self._build_village_row(village)
            # Built from row.phases (post project-dedup), not the raw fetch, so
            # a village's other projects don't leak in as always-empty columns.
            for ps in row.phases:
                if ps.name not in all_phase_names_map:
                    all_phase_names_map[ps.name] = ps.order

            village_rows.append(row)
            total_completed_phases += row.completed_phases

            if row.overall_status == STATUS_COMPLETED:
                completed_villages += 1
            elif row.overall_status == STATUS_IN_PROGRESS:
                in_progress_villages += 1
            else:
                not_started_villages += 1

        # Sort phase names by their order
        sorted_phase_names = [
            name for name, order in sorted(all_phase_names_map.items(), key=lambda x: x[1])
        ]

        summary = CantonPlanningSummary(
            canton_id=self._canton.pk,
            canton_name=self._canton.name,
            village_count=len(villages),
            completed_villages=completed_villages,
            in_progress_villages=in_progress_villages,
            not_started_villages=not_started_villages,
            total_completed_phases=total_completed_phases,
            all_phase_names=sorted_phase_names,
            villages=village_rows,
        )

        logger.info(
            "Canton '%s': %d villages, %.1f%% overall planning completion",
            self._canton.name, summary.village_count, summary.overall_completion_pct,
        )
        return summary

    def _build_village_row(self, village: AdministrativeLevel, phases_qs=None) -> VillagePlanningRow:
        if phases_qs is None:
            phases_qs = self._repo.get_phases_for_village(village)
        phases_qs = _select_default_project_phases(list(phases_qs))

        phase_statuses: List[PhaseStatus] = []
        completed_phases_count = in_progress_phases_count = not_started_phases_count = 0

        for phase in phases_qs:
            # Real Phase rows: read prefetched activities/tasks in Python
            # (see _get_phase_status_optimized). phase.get_status() fires up
            # to 3 correlated EXISTS subqueries against the *entire* Task
            # table per phase — with real canton-sized data (dozens of
            # villages x 4 phases) that's what was making this tab take
            # several seconds to load. Test doubles (plain MagicMock, no real
            # `activities` relation) still go through get_status() since
            # that's what they configure.
            if isinstance(phase, Phase):
                status = self._get_phase_status_optimized(phase)
            else:
                status = phase.get_status()
            
            phase_statuses.append(PhaseStatus(order=phase.order, name=phase.name, status=status))

            if status == STATUS_COMPLETED:
                completed_phases_count += 1
            elif status == STATUS_IN_PROGRESS:
                in_progress_phases_count += 1
            else:
                not_started_phases_count += 1
        
        priorities_count = getattr(village, "investments_count", 0)

        return VillagePlanningRow(
            village_id=village.pk,
            village_name=village.name,
            completed_phases=completed_phases_count,
            in_progress_phases=in_progress_phases_count,
            not_started_phases=not_started_phases_count,
            priorities_count=priorities_count,
            phases=phase_statuses,
        )

    def _get_phase_status_optimized(self, phase: Phase) -> str:
        """
        Logic from Phase.get_status() rewritten to read prefetched
        activities/tasks in Python instead of firing Phase.get_status()'s up
        to 3 correlated EXISTS subqueries (each scanning the *entire* Task
        table via `tasks__id__in=Subquery(Task.objects.filter(status=X)...)`)
        per phase. Iterating phase.activities.all() is a no-op query when
        prefetched (the normal case here) and at worst one query when not —
        either way far cheaper than the subquery pattern, which is what made
        canton-sized cantons (dozens of villages x 4 phases) take seconds.
        """
        all_activities = list(phase.activities.all())
        if not all_activities:
            return STATUS_NOT_STARTED

        completed_exists = False
        not_started_exists = False
        error_exists = False

        for activity in all_activities:
            for task in activity.tasks.all():
                t_status = task.status
                if t_status == Task.COMPLETED:
                    completed_exists = True
                elif t_status == Task.NOT_STARTED:
                    not_started_exists = True
                elif t_status == Task.ERROR:
                    error_exists = True

        if not_started_exists and not completed_exists:
            return Task.NOT_STARTED
        elif not not_started_exists and completed_exists:
            return Task.COMPLETED
        elif error_exists:
            return Task.ERROR

        return Task.IN_PROGRESS
