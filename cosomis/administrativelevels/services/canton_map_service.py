"""
canton_map_service.py
---------------------
Service that computes the geographic data required by the Canton Profile Map tab.
All aggregation lives here — never in views or templates (hexagonal architecture).

Color strategy
~~~~~~~~~~~~~~~
Colors are assigned by **Category name** (Category.name, e.g. "Education",
"Energie", "Sante"), NOT by Sector name, because sector names are free-text
and not standardized.  A deterministic round-robin palette is used so new
categories automatically get a distinct color with zero configuration.
"""

import logging
from typing import Any

from django.db.models import Prefetch

from administrativelevels.models import AdministrativeLevel, Phase, Task
from investments.models import Investment

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palette — assigned round-robin to category names as encountered.
# ---------------------------------------------------------------------------
_PALETTE: list[str] = [
    "#3B82F6",  # blue
    "#EF4444",  # red
    "#06B6D4",  # cyan
    "#84CC16",  # lime-green
    "#F59E0B",  # amber
    "#8B5CF6",  # violet
    "#10B981",  # emerald
    "#F97316",  # orange
    "#EC4899",  # pink
    "#14B8A6",  # teal
]

NO_PRIORITY_COLOR = "#9CA3AF"  # light grey — village without a priority
PLANNING_COMPLETED = "#22C55E"  # green
PLANNING_IN_PROGRESS = "#EAB308"  # yellow
PLANNING_NOT_STARTED = "#EF4444"  # red


class _CategoryColorRegistry:
    """
    Assigns a stable hex color to each unique category name encountered
    within a single service call.  Same name → same color always.
    """

    def __init__(self) -> None:
        self._map: dict[str, str] = {}  # lower-key → hex

    def color_for(self, category_name: str | None) -> str:
        if not category_name:
            return _PALETTE[0]
        key = category_name.strip().lower()
        if key not in self._map:
            idx = len(self._map) % len(_PALETTE)
            self._map[key] = _PALETTE[idx]
        return self._map[key]

    def legend_entries(self) -> list[dict[str, str]]:
        """Return [{name, color}] in first-seen order for the map legend."""
        return [
            {"name": key.title(), "color": color}
            for key, color in self._map.items()
        ]


class CantonMapService:
    """
    Builds a JSON-serialisable dict that feeds all three Canton map layers.

    Usage:
        service = CantonMapService(canton)
        geo_data = service.get_villages_geo_data()   # → dict
    """

    def __init__(self, canton: AdministrativeLevel) -> None:
        assert canton.type == AdministrativeLevel.CANTON, (
            "CantonMapService must receive a Canton-type AdministrativeLevel"
        )
        self._canton = canton
        self._color_registry = _CategoryColorRegistry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_villages_geo_data(self) -> dict[str, Any]:
        """
        Returns a dict with:
          - 'features'       : list of village feature dicts (one per village)
          - 'subprojects'    : list of active investments with coords (sidebar)
          - 'bounds'         : [[min_lng, min_lat], [max_lng, max_lat]] or None
          - 'category_legend': [{name, color}] for the priorities/subprojects legend
        """
        villages = self._fetch_villages()

        # Build features first so the registry is populated before legend_entries()
        features = [self._build_feature(v) for v in villages]

        coords_list = [
            (float(v.longitude), float(v.latitude))
            for v in villages
            if v.latitude is not None and v.longitude is not None
        ]

        subprojects = self._build_subprojects_list(villages)

        logger.debug(
            "CantonMapService: canton=%s villages=%d subprojects=%d",
            self._canton.name,
            len(features),
            len(subprojects),
        )

        return {
            "features": features,
            "subprojects": subprojects,
            "bounds": self._compute_bounds(coords_list) if coords_list else None,
            "category_legend": self._color_registry.legend_entries(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_villages(self) -> list[AdministrativeLevel]:
        """Fetch villages with investments and phases prefetched (no N+1)."""
        return list(
            AdministrativeLevel.objects.filter(
                parent=self._canton,
                type=AdministrativeLevel.VILLAGE,
            )
            .prefetch_related(
                # investments for priorities and subprojects layers
                Prefetch(
                    "investments",
                    queryset=Investment.objects.select_related(
                        "sector", "sector__category"
                    ).only(
                        "id", "ranking", "title", "estimated_cost",
                        "project_status", "climate_contribution",
                        "administrative_level_id", "sector",
                    ),
                ),
                # phases → activities → tasks for planning layer
                Prefetch(
                    "phases",
                    queryset=Phase.objects.prefetch_related(
                        Prefetch(
                            "activities__tasks",
                            queryset=Task.objects.only("id", "status", "activity_id"),
                        )
                    ).only("id", "name", "order", "village_id"),
                ),
            )
            .only(
                "id", "name", "latitude", "longitude",
                "total_population", "identified_priority",
            )
        )

    def _get_category_name(self, investment: Investment) -> str | None:
        """Extract the Category.name from an investment's sector, or None."""
        try:
            if investment.sector and investment.sector.category:
                return investment.sector.category.name
        except AttributeError:
            pass
        return None

    def _build_feature(self, village: AdministrativeLevel) -> dict[str, Any]:
        """Build a single feature dict for one village covering all layers."""
        investments = list(village.investments.all())
        active_investments = [
            inv for inv in investments
            if inv.project_status != Investment.NOT_FUNDED
        ]
        top_priority = self._get_top_priority(investments)

        # ---- Priorities layer ----
        if top_priority:
            category_name = self._get_category_name(top_priority)
            sector_name = top_priority.sector.name if top_priority.sector else None
            priority_color = self._color_registry.color_for(category_name)
            has_priority = True
        else:
            category_name = None
            sector_name = None
            priority_color = NO_PRIORITY_COLOR
            has_priority = False

        # ---- Subprojects layer ----
        # Use the category of the first active investment for the ring color
        has_subprojects = bool(active_investments)
        sub_category_name = None
        sub_category_color = NO_PRIORITY_COLOR
        if active_investments:
            sub_category_name = self._get_category_name(active_investments[0])
            sub_category_color = self._color_registry.color_for(sub_category_name)

        # ---- Planning layer ----
        planning_status = self._compute_planning_status(village)
        planning_color = {
            "completed": PLANNING_COMPLETED,
            "in_progress": PLANNING_IN_PROGRESS,
            "not_started": PLANNING_NOT_STARTED,
        }[planning_status]

        return {
            "id": village.id,
            "name": village.name,
            "latitude": float(village.latitude) if village.latitude else None,
            "longitude": float(village.longitude) if village.longitude else None,
            "population": village.total_population,
            # Priorities layer
            "has_priority": has_priority,
            "category_name": category_name,
            "sector_name": sector_name,
            "priority_color": priority_color,
            "top_priority": {
                "id": top_priority.id,
                "title": top_priority.title,
                "cost": top_priority.estimated_cost,
                "climate": top_priority.climate_contribution,
            } if top_priority else None,
            # Subprojects layer
            "has_subprojects": has_subprojects,
            "subprojects_count": len(active_investments),
            "sub_category_name": sub_category_name,
            "sub_category_color": sub_category_color,
            # Planning layer
            "planning_status": planning_status,
            "planning_color": planning_color,
            "phases_total": sum(1 for _ in village.phases.all()),
            "phases_complete": sum(
                1 for ph in village.phases.all()
                if self._phase_status(ph) == "completed"
            ),
        }

    @staticmethod
    def _get_top_priority(investments: list[Investment]) -> Investment | None:
        """Return the highest-ranked unfunded investment (priority), or None."""
        unfunded = [i for i in investments if i.project_status == Investment.NOT_FUNDED]
        if not unfunded:
            return None
        return min(unfunded, key=lambda i: i.ranking or 9999)

    @staticmethod
    def _phase_status(phase: Phase) -> str:
        """Determine the status of a phase based on its tasks."""
        statuses = [
            task.status
            for activity in phase.activities.all()
            for task in activity.tasks.all()
        ]
        if not statuses:
            return "not_started"
        if all(s == Task.COMPLETED for s in statuses):
            return "completed"
        if all(s == Task.NOT_STARTED for s in statuses):
            return "not_started"
        return "in_progress"

    def _compute_planning_status(self, village: AdministrativeLevel) -> str:
        """Return 'completed' | 'in_progress' | 'not_started' for a village."""
        phases = list(village.phases.all())
        if not phases:
            return "not_started"
        statuses = [self._phase_status(ph) for ph in phases]
        if all(s == "completed" for s in statuses):
            return "completed"
        if all(s == "not_started" for s in statuses):
            return "not_started"
        return "in_progress"

    def _build_subprojects_list(
            self, villages: list[AdministrativeLevel]
    ) -> list[dict[str, Any]]:
        """Flat list of active investments — feeds the sidebar and subprojects layer."""
        result = []
        for village in villages:
            for inv in village.investments.all():
                if inv.project_status == Investment.NOT_FUNDED:
                    continue
                category_name = self._get_category_name(inv)
                category_color = self._color_registry.color_for(category_name)
                result.append({
                    "id": inv.id,
                    "title": inv.title,
                    "village_id": village.id,
                    "village_name": village.name,
                    "latitude": float(village.latitude) if village.latitude else None,
                    "longitude": float(village.longitude) if village.longitude else None,
                    "sector_name": inv.sector.name if inv.sector else None,
                    "category_name": category_name,
                    "category_color": category_color,
                    "estimated_cost": inv.estimated_cost,
                    "project_status": inv.project_status,
                })
        # Sort by estimated_cost descending
        result.sort(key=lambda x: x["estimated_cost"] or 0, reverse=True)
        return result

    @staticmethod
    def _compute_bounds(
            coords: list[tuple[float, float]]
    ) -> list[list[float]] | None:
        """
        Compute [[min_lng, min_lat], [max_lng, max_lat]] bounding box.
        Returns None if no coordinates are available.
        """
        if not coords:
            return None
        lngs = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        padding = 0.05
        return [
            [min(lngs) - padding, min(lats) - padding],
            [max(lngs) + padding, max(lats) + padding],
        ]
