from dataclasses import dataclass, field
from typing import List, Dict, Optional

from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel, Task
from investments.models import Investment


@dataclass
class FunnelStage:
    key: str
    label: str
    description: str
    icon: str
    color: str
    count: int = 0
    pct_of_total: float = 0.0
    pct_from_previous: float = 0.0
    polygon_points: str = ""
    label_y: float = 0.0
    width_top: float = 0.0
    width_mid: float = 0.0


@dataclass
class FunnelSummary:
    stages: List[FunnelStage]
    phase_status_dist: Dict[str, int]
    investment_status_dist: Dict[str, int]
    sector_breakdown: List[dict]
    total_estimated_cost: int
    total_funded_cost: int
    total_completed_cost: int
    total_investments: int
    funded_investments: int
    completed_investments: int
    generated_at: str
    funnel_width: int = 720
    funnel_height: int = 0


class CountryCddFunnelService:
    """Aggregates a country-wide funnel of the CDD process.

    Stages walk a village from "exists in the dataset" through "CDD process
    engaged", "planning complete", "priorities identified", "funded",
    "in execution", to "completed infrastructure". A village can be at
    multiple stages simultaneously; each stage is an independent count of
    villages that have reached that point.
    """

    STAGE_DEFS = [
        (
            "all_villages",
            _("All Villages"),
            _("Total villages in the country dataset"),
            "home",
            "#6366f1",
        ),
        (
            "engaged",
            _("CDD Engaged"),
            _("Villages where the CDD process has been initiated"),
            "users",
            "#4f46e5",
        ),
        (
            "planning_complete",
            _("Planning Complete"),
            _("Villages where every planning task is completed"),
            "clipboard",
            "#4338ca",
        ),
        (
            "priorities",
            _("Priorities Identified"),
            _("Villages with at least one investment priority"),
            "lightbulb",
            "#7c3aed",
        ),
        (
            "funded",
            _("Funded"),
            _("Villages with at least one funded investment"),
            "dollar",
            "#9333ea",
        ),
        (
            "in_execution",
            _("In Execution"),
            _("Villages with infrastructure under construction"),
            "tool",
            "#db2777",
        ),
        (
            "completed",
            _("Completed"),
            _("Villages with completed infrastructure"),
            "flag",
            "#10b981",
        ),
    ]

    STAGE_HEIGHT = 78
    FUNNEL_WIDTH = 720
    MIN_RATIO = 0.10

    def __init__(self):
        self._village_qs = AdministrativeLevel.objects.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
        )

    def get_summary(self) -> FunnelSummary:
        counts = self._compute_stage_counts()
        stages = self._build_stages(counts)
        self._assign_polygons(stages)

        phase_dist = self._phase_status_distribution()
        inv_dist = self._investment_status_distribution()
        sectors = self._sector_breakdown()
        cost = self._cost_aggregates()
        inv_counts = self._investment_counts()

        return FunnelSummary(
            stages=stages,
            phase_status_dist=phase_dist,
            investment_status_dist=inv_dist,
            sector_breakdown=sectors,
            total_estimated_cost=cost["estimated"],
            total_funded_cost=cost["funded"],
            total_completed_cost=cost["completed"],
            total_investments=inv_counts["total"],
            funded_investments=inv_counts["funded"],
            completed_investments=inv_counts["completed"],
            generated_at=timezone.now().isoformat(),
            funnel_width=self.FUNNEL_WIDTH,
            funnel_height=self.STAGE_HEIGHT * len(stages),
        )

    def _compute_stage_counts(self) -> Dict[str, int]:
        total = self._village_qs.count()
        engaged = self._village_qs.filter(phases__isnull=False).distinct().count()
        planning_complete = (
            self._village_qs.filter(phases__activities__tasks__status=Task.COMPLETED)
            .exclude(
                phases__activities__tasks__status__in=[
                    Task.NOT_STARTED,
                    Task.IN_PROGRESS,
                    Task.ERROR,
                ]
            )
            .distinct()
            .count()
        )
        priorities = (
            self._village_qs.filter(investments__isnull=False).distinct().count()
        )
        funded = (
            self._village_qs.filter(
                investments__project_status__in=[
                    Investment.FUNDED,
                    Investment.IN_PROGRESS,
                    Investment.COMPLETED,
                ]
            )
            .distinct()
            .count()
        )
        in_execution = (
            self._village_qs.filter(
                investments__project_status__in=[
                    Investment.IN_PROGRESS,
                    Investment.COMPLETED,
                ]
            )
            .distinct()
            .count()
        )
        completed = (
            self._village_qs.filter(
                investments__project_status=Investment.COMPLETED
            )
            .distinct()
            .count()
        )
        return {
            "all_villages": total,
            "engaged": engaged,
            "planning_complete": planning_complete,
            "priorities": priorities,
            "funded": funded,
            "in_execution": in_execution,
            "completed": completed,
        }

    def _build_stages(self, counts: Dict[str, int]) -> List[FunnelStage]:
        stages: List[FunnelStage] = []
        total = counts["all_villages"] or 1
        prev_count: Optional[int] = None
        for key, label, description, icon, color in self.STAGE_DEFS:
            count = counts[key]
            pct_total = (count / total) * 100 if total else 0.0
            if prev_count is None:
                pct_prev = 100.0
            elif prev_count == 0:
                pct_prev = 0.0
            else:
                pct_prev = (count / prev_count) * 100
            stages.append(
                FunnelStage(
                    key=key,
                    label=str(label),
                    description=str(description),
                    icon=icon,
                    color=color,
                    count=count,
                    pct_of_total=round(pct_total, 1),
                    pct_from_previous=round(pct_prev, 1),
                )
            )
            prev_count = count
        return stages

    def _assign_polygons(self, stages: List[FunnelStage]) -> None:
        """Compute trapezoid polygon points for the SVG funnel.

        Funnel shape is forced monotonically non-increasing so each band is
        no wider than the one above it, even when the underlying counts are
        not perfectly nested (e.g. a village can have an Investment priority
        without having every planning task completed). The numeric label
        always reflects the true stage count.
        """
        if not stages:
            return
        baseline = stages[0].count or 1
        width = self.FUNNEL_WIDTH
        height = self.STAGE_HEIGHT

        display_ratios = []
        prev_ratio = 1.0
        for stage in stages:
            raw = stage.count / baseline if baseline else 0
            ratio = min(raw, prev_ratio)
            ratio = max(ratio, self.MIN_RATIO if stage.count > 0 else self.MIN_RATIO * 0.55)
            display_ratios.append(ratio)
            prev_ratio = ratio

        for i, stage in enumerate(stages):
            ratio_top = display_ratios[i]
            ratio_bot = display_ratios[i + 1] if i + 1 < len(display_ratios) else max(
                ratio_top * 0.85, self.MIN_RATIO * 0.55
            )
            w_top = width * ratio_top
            w_bot = width * ratio_bot
            x_tl = (width - w_top) / 2
            x_tr = x_tl + w_top
            x_bl = (width - w_bot) / 2
            x_br = x_bl + w_bot
            y_t = i * height
            y_b = y_t + height
            stage.polygon_points = (
                f"{x_tl:.1f},{y_t} {x_tr:.1f},{y_t} "
                f"{x_br:.1f},{y_b} {x_bl:.1f},{y_b}"
            )
            stage.label_y = y_t + height / 2
            stage.width_top = w_top
            stage.width_mid = (w_top + w_bot) / 2

    def _phase_status_distribution(self) -> Dict[str, int]:
        rows = Task.objects.values("status").annotate(c=Count("id"))
        return {r["status"]: r["c"] for r in rows}

    def _investment_status_distribution(self) -> Dict[str, int]:
        rows = Investment.objects.values("project_status").annotate(c=Count("id"))
        return {r["project_status"]: r["c"] for r in rows}

    def _sector_breakdown(self) -> List[dict]:
        rows = (
            Investment.objects.values("sector__name")
            .annotate(count=Count("id"), total_cost=Sum("estimated_cost"))
            .order_by("-count")[:8]
        )
        return [
            {
                "name": r["sector__name"] or _("Unspecified"),
                "count": r["count"],
                "total_cost": r["total_cost"] or 0,
            }
            for r in rows
        ]

    def _cost_aggregates(self) -> Dict[str, int]:
        estimated = (
            Investment.objects.aggregate(s=Sum("estimated_cost"))["s"] or 0
        )
        funded = (
            Investment.objects.filter(
                project_status__in=[
                    Investment.FUNDED,
                    Investment.IN_PROGRESS,
                    Investment.COMPLETED,
                ]
            ).aggregate(s=Sum("estimated_cost"))["s"]
            or 0
        )
        completed = (
            Investment.objects.filter(
                project_status=Investment.COMPLETED
            ).aggregate(s=Sum("estimated_cost"))["s"]
            or 0
        )
        return {"estimated": estimated, "funded": funded, "completed": completed}

    def _investment_counts(self) -> Dict[str, int]:
        total = Investment.objects.count()
        funded = Investment.objects.filter(
            project_status__in=[
                Investment.FUNDED,
                Investment.IN_PROGRESS,
                Investment.COMPLETED,
            ]
        ).count()
        completed = Investment.objects.filter(
            project_status=Investment.COMPLETED
        ).count()
        return {"total": total, "funded": funded, "completed": completed}

    def get_villages_at_stage(self, stage_key: str):
        qs = self._village_qs.select_related("parent")
        if stage_key == "all_villages":
            return qs.order_by("name")
        if stage_key == "engaged":
            return qs.filter(phases__isnull=False).distinct().order_by("name")
        if stage_key == "planning_complete":
            return (
                qs.filter(phases__activities__tasks__status=Task.COMPLETED)
                .exclude(
                    phases__activities__tasks__status__in=[
                        Task.NOT_STARTED,
                        Task.IN_PROGRESS,
                        Task.ERROR,
                    ]
                )
                .distinct()
                .order_by("name")
            )
        if stage_key == "priorities":
            return (
                qs.filter(investments__isnull=False).distinct().order_by("name")
            )
        if stage_key == "funded":
            return (
                qs.filter(
                    investments__project_status__in=[
                        Investment.FUNDED,
                        Investment.IN_PROGRESS,
                        Investment.COMPLETED,
                    ]
                )
                .distinct()
                .order_by("name")
            )
        if stage_key == "in_execution":
            return (
                qs.filter(
                    investments__project_status__in=[
                        Investment.IN_PROGRESS,
                        Investment.COMPLETED,
                    ]
                )
                .distinct()
                .order_by("name")
            )
        if stage_key == "completed":
            return (
                qs.filter(investments__project_status=Investment.COMPLETED)
                .distinct()
                .order_by("name")
            )
        return qs.none()

    @classmethod
    def stage_label(cls, stage_key: str) -> str:
        for key, label, *_rest in cls.STAGE_DEFS:
            if key == stage_key:
                return str(label)
        return ""
