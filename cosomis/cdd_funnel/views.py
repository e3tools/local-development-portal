import json

from django.core.paginator import Paginator
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.views import generic

from administrativelevels.models import Task
from cosomis.mixins import PageMixin
from investments.models import Investment

from cdd_funnel.services import CountryCddFunnelService


# Display labels for raw Task / Investment status codes so the template can
# render them without re-deriving the choices map.
TASK_STATUS_LABELS = {
    Task.NOT_STARTED: _("Not started"),
    Task.IN_PROGRESS: _("In progress"),
    Task.COMPLETED: _("Completed"),
    Task.ERROR: _("Error"),
}

TASK_STATUS_COLORS = {
    Task.NOT_STARTED: "#cbd5e1",
    Task.IN_PROGRESS: "#f59e0b",
    Task.COMPLETED: "#10b981",
    Task.ERROR: "#ef4444",
}

INVESTMENT_STATUS_LABELS = {
    Investment.NOT_FUNDED: _("Not funded"),
    Investment.FUNDED: _("Funded"),
    Investment.IN_PROGRESS: _("In progress"),
    Investment.COMPLETED: _("Completed"),
    Investment.PAUSED: _("Paused"),
}

INVESTMENT_STATUS_COLORS = {
    Investment.NOT_FUNDED: "#cbd5e1",
    Investment.FUNDED: "#6366f1",
    Investment.IN_PROGRESS: "#f59e0b",
    Investment.COMPLETED: "#10b981",
    Investment.PAUSED: "#9ca3af",
}


def _build_chart_dataset(distribution, label_map, color_map):
    labels, values, colors, items = [], [], [], []
    for key, label in label_map.items():
        count = distribution.get(key, 0)
        if count == 0:
            continue
        labels.append(str(label))
        values.append(count)
        colors.append(color_map.get(key, "#9ca3af"))
        items.append({"label": str(label), "count": count, "color": color_map.get(key, "#9ca3af")})
    return {
        "labels_json": json.dumps(labels),
        "values_json": json.dumps(values),
        "colors_json": json.dumps(colors),
        "items": items,
        "total": sum(values),
    }


class CddFunnelView(PageMixin, generic.TemplateView):
    template_name = "cdd_funnel.html"
    title = _("CDD Funnel")
    active_level1 = "cdd_funnel"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        summary = CountryCddFunnelService().get_summary()

        task_chart = _build_chart_dataset(
            summary.phase_status_dist, TASK_STATUS_LABELS, TASK_STATUS_COLORS
        )
        investment_chart = _build_chart_dataset(
            summary.investment_status_dist,
            INVESTMENT_STATUS_LABELS,
            INVESTMENT_STATUS_COLORS,
        )

        max_sector_count = max(
            (s["count"] for s in summary.sector_breakdown), default=0
        )

        ctx.update(
            {
                "summary": summary,
                "stages": summary.stages,
                "first_stage": summary.stages[0] if summary.stages else None,
                "last_stage": summary.stages[-1] if summary.stages else None,
                "engaged_stage": next(
                    (s for s in summary.stages if s.key == "engaged"), None
                ),
                "funded_stage": next(
                    (s for s in summary.stages if s.key == "funded"), None
                ),
                "task_chart": task_chart,
                "investment_chart": investment_chart,
                "max_sector_count": max_sector_count,
            }
        )
        return ctx


class StageDrilldownView(generic.TemplateView):
    """HTMX fragment: list of villages currently at a given funnel stage."""

    template_name = "_stage_villages.html"
    paginate_by = 24

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        stage_key = kwargs.get("stage_key")
        service = CountryCddFunnelService()
        stage_label = service.stage_label(stage_key)
        if not stage_label:
            raise Http404("Unknown stage")

        villages_qs = service.get_villages_at_stage(stage_key)
        paginator = Paginator(villages_qs, self.paginate_by)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        ctx.update(
            {
                "stage_key": stage_key,
                "stage_label": stage_label,
                "page_obj": page_obj,
                "total": paginator.count,
            }
        )
        return ctx
