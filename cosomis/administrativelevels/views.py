import json
import os
import re
import zipfile
from io import BytesIO
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import QuerySet, Sum, Count, Subquery, Q, Case, When, F, IntegerField, Value, Prefetch
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, ListView, CreateView, FormView, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import BaseFormView

from administrativelevels.forms import (
    AdministrativeLevelForm,
    AttachmentFilterForm,
    BulkUploadInvestmentsForm,
    ProjectForm,
    UpdateInvestmentForm,
    VillageSearchForm,
)
from administrativelevels.models import AdministrativeLevel, Phase, Task, Project, Category, Sector, Activity
from administrativelevels.services.canton_map_service import CantonMapService
from administrativelevels.services.canton_planning_service import CantonPlanningService
from administrativelevels.services.canton_summary_service import CantonSummaryService
from cosomis.constants import IMAGE_EXTENSIONS
from cosomis.mixins import PageMixin, LoginRequiredApproveRequiredMixin, GRMMixin
from cosomis.utils_functions import get_api_datas
from investments.domain.investment_criteria import InvestmentCriteria
from investments.infrastructure.repositories.db_investment_repository import DbInvestmentRepository
from investments.models import Attachment, Investment, Package, PackageFundedInvestment
from static.config.datatable import get_datatable_config
from usermanager.permissions import AdminPermissionRequiredMixin, IsInvestorMixin
from utils.mixpanel.utils import track_user_activity


class AdministrativeLevelsListView(PageMixin, LoginRequiredApproveRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = []  # AdministrativeLevel.objects.filter(type="Village")
    template_name = "administrative_level/list.html"
    context_object_name = "administrativelevels"
    title = _("Administrative levels")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        _type = self.request.GET.get("type", "Village")
        # `type` is stored in different casings across datasets (e.g. "Village"
        # in the Togo seed vs "village" in the Benin dump), so always compare
        # case-insensitively. Ordered by name so pagination is deterministic.
        base = AdministrativeLevel.objects.filter(type__iexact=_type).order_by("name")
        if search:
            if search == "All":
                return Paginator(base, base.count() or 1).get_page(page_number)
            search = search.upper()
            return Paginator(base.filter(name__icontains=search), 100).get_page(page_number)
        return Paginator(base, 100).get_page(page_number)

        # return super().get_queryset()

    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelsListView, self).get_context_data(**kwargs)
        ctx["search"] = self.request.GET.get("search", None)
        ctx["type"] = self.request.GET.get("type", "Village")
        return ctx


class AdministrativeLevelCreateView(
    PageMixin, LoginRequiredApproveRequiredMixin, AdminPermissionRequiredMixin, CreateView
):
    model = AdministrativeLevel
    template_name = "administrative_level/create.html"
    context_object_name = "administrativelevel"
    title = _("Create Administrative level")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_parent(self, type: str):
        parent = None
        if type == "Prefecture":
            parent = "Region"
        elif type == "Commune":
            parent = "Prefecture"
        elif type == "Canton":
            parent = "Commune"
        elif type == "Village":
            parent = "Canton"
        return parent

    form_class = AdministrativeLevelForm  # specify the class form to be displayed

    def get_context_data(self, **kwargs):
        type = self.request.GET.get("type")
        context = super().get_context_data(**kwargs)
        context["form"] = AdministrativeLevelForm(self.get_parent(type), type)
        return context

    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelForm(
            self.get_parent(self.request.GET.get("type")), request.POST
        )
        if form.is_valid():
            form.save()
            return redirect("administrativelevels:list")
        return super(AdministrativeLevelCreateView, self).get(request, *args, **kwargs)


class AdministrativeLevelSearchListView(PageMixin, LoginRequiredApproveRequiredMixin, ListView):
    """Display administrative level list by parent choice"""

    model = AdministrativeLevel
    queryset = []
    template_name = "administrative_level/list.html"
    context_object_name = "administrativelevels"
    title = _("Administrative levels")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        _type = self.request.GET.get("type", "Village")
        # `type` is stored in different casings across datasets (e.g. "Village"
        # in the Togo seed vs "village" in the Benin dump), so always compare
        # case-insensitively. Ordered by name so pagination is deterministic.
        base = AdministrativeLevel.objects.filter(type__iexact=_type).order_by("name")
        if search:
            if search == "All":
                return Paginator(base, base.count() or 1).get_page(page_number)
            search = search.upper()
            return Paginator(base.filter(name__icontains=search), 100).get_page(page_number)
        return Paginator(base, 100).get_page(page_number)

    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelSearchListView, self).get_context_data(**kwargs)
        # Pull the actual level names from the data so the form labels, select2
        # placeholders, and the "Choice the X in Y" / "See X" copy can match
        # the dataset's vocabulary (Country/Département/... for Benin,
        # Region/Prefecture/... for Togo, etc.).
        hierarchy_labels = AdministrativeLevel.get_hierarchy_labels()
        # When the dataset has a single root (e.g. Benin = one "country" row),
        # hide the top-level dropdown and pre-populate the next level.
        roots = AdministrativeLevel.objects.filter(parent__isnull=True)
        single_region = roots.first() if roots.count() == 1 else None
        ctx["single_region"] = single_region
        ctx["form"] = VillageSearchForm(
            hierarchy_labels=hierarchy_labels,
            single_region=single_region,
            initial={"region": single_region} if single_region else None,
        )
        ctx["search"] = self.request.GET.get("search", None)
        ctx["type"] = self.request.GET.get("type", "Village")
        ctx["current_language"] = translation.get_language()
        ctx["hierarchy_labels"] = hierarchy_labels
        ctx["leaf_label"] = hierarchy_labels[-1] if hierarchy_labels else _("Village")
        ctx["parent_of_leaf_label"] = (
            hierarchy_labels[-2] if len(hierarchy_labels) >= 2 else _("Canton")
        )
        return ctx


class AdministrativeLevelDetailView(PageMixin, GRMMixin, LoginRequiredApproveRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = "administrative_level/detail/index.html"
    active_level1 = "administrative_levels"

    def __init__(self):
        super().__init__()
        self.__investment_repository = DbInvestmentRepository()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'cart-toggle' in request.POST:
            investment = Investment.objects.get(id=request.POST['cart-toggle'])
            if investment.project_status == Investment.NOT_FUNDED:
                package = Package.objects.get_active_cart(user=self.request.user)
                if package.funded_investments.filter(id=investment.id).exists():
                    package.funded_investments.remove(investment)
                    track_user_activity(request, 'RemoveInvestmentInPackage')
                else:
                    package.funded_investments.add(investment)
                    track_user_activity(request, 'AddInvestmentInPackage')
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AdministrativeLevelDetailView, self).get_context_data(**kwargs)

        images_extensions_query = Q()
        for ext in IMAGE_EXTENSIONS:
            images_extensions_query |= Q(url__icontains=ext)

        if "object" in context:
            context["title"] = "%s %s" % (_(context['object'].type), context['object'].name)
            if context["object"].is_village():
                # context["investments"] = self.__investment_repository.find_by_criteria(InvestmentCriteria(administrative_level=self.object))
                context['geo_segment'] = context["object"].geo_segment
        admin_level = context.get("object")

        context["context_object_name"] = admin_level.type.lower()

        if admin_level.children.all():
            context['children_services_infrastructures'], context[
                'children_services_infrastructures_total_ids'] = self.__get_upper_services_infrastructure(admin_level)
            context['children_services_infrastructures_total_ids'] = list(
                set(context['children_services_infrastructures_total_ids']))

        context['phases'] = self._get_planning_cycle()
        context['development_plan'] = self._get_development_plan(context['phases'])

        tasks_qs = Task.objects.filter(activity__phase__village=admin_level)
        current_task = admin_level.get_current_task()
        current_activity = current_task.activity if current_task else None
        current_phase = current_activity.phase if current_activity else None

        task_number = tasks_qs.count()
        tasks_done = tasks_qs.filter(status=Task.COMPLETED).count()
        context["planning_status"] = {
            "current_phase": current_phase,
            "current_activity": current_activity,
            "current_task": current_task,
            "completed": round(float(tasks_done) * 100 / float(task_number), 2) if task_number != 0 else '-',
            "priorities_identified": context["object"].identified_priority,
            "village_development_plan_date": "",
            "facilitator": "",
        }

        images_number = 5
        # Walk the subtree iteratively (one query per tree level) so the
        # carousel on region/prefecture pages can surface images attached to
        # descendant villages, not just the level itself. is_village() is the
        # fast path — no descendants to walk.
        level_ids = [admin_level.id]
        if not admin_level.is_village():
            frontier = [admin_level.id]
            while frontier:
                next_ids = list(
                    AdministrativeLevel.objects.filter(parent_id__in=frontier)
                    .values_list('id', flat=True)
                )
                if not next_ids:
                    break
                level_ids.extend(next_ids)
                frontier = next_ids

        subtree_q = (
            Q(adm_id__in=level_ids) |
            Q(task__activity__phase__village_id__in=level_ids)
        )

        completed = Attachment.objects.filter(
            subtree_q,
            process_moment=Attachment.COMPLETED_INFRASTRUCTURE
        ).filter(images_extensions_query)[:3]
        in_progress = []
        if not completed:
            in_progress = Attachment.objects.filter(
                subtree_q,
                process_moment=Attachment.INFRASTRUCTURE_IN_PROGRESS
            ).filter(images_extensions_query)[:1]

        community = Attachment.objects.filter(
            subtree_q,
            process_moment=Attachment.COMMUNITY_PROCESS
        ).filter(images_extensions_query)[:(images_number - len(completed) - len(in_progress))]

        images = list(completed) + list(in_progress) + list(community)
        # images = Attachment.objects.filter(
        #     Q (adm=admin_level) |
        #     Q (task__activity__phase__village=admin_level)
        # ).exclude(url__icontains='.pdf').all()[:5]
        context["images_data"] = {
            "images": images,
            "exists_at_least_image": len(images) != 0,
            "first_image": images[0] if len(images) > 0 else None,
        }

        # Always display village priorities in ranking order, regardless of
        # funding state. NULL rankings sink to the bottom so legacy rows
        # without a ranking don't jump to the top.
        context["investments"] = self.__investment_repository.find_by_criteria(
            InvestmentCriteria(administrative_level=self.object)
        ).order_by(F('ranking').asc(nulls_last=True), 'id')

        # Non-village levels (region/prefecture/etc.) have no direct
        # population, planning, or investment rows of their own — every
        # data point lives on descendant villages. Aggregate from the
        # subtree we already walked above for the carousel.
        if not admin_level.is_village():
            descendant_villages = AdministrativeLevel.objects.filter(
                id__in=level_ids
            ).filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
            )
            descendant_village_ids = list(
                descendant_villages.values_list('id', flat=True)
            )
            village_count = len(descendant_village_ids)

            pop_agg = descendant_villages.aggregate(
                total=Coalesce(Sum('total_population'), 0),
                men=Coalesce(Sum('population_men'), 0),
                women=Coalesce(Sum('population_women'), 0),
                young=Coalesce(Sum('population_young'), 0),
                elder=Coalesce(Sum('population_elder'), 0),
                handicap=Coalesce(Sum('population_handicap'), 0),
                agriculturist=Coalesce(Sum('population_agriculturist'), 0),
                pastoralist=Coalesce(Sum('population_pastoralist'), 0),
                minorities=Coalesce(Sum('population_minorities'), 0),
            )
            context["population"] = {
                **pop_agg,
                "village_count": village_count,
            }

            if descendant_village_ids:
                agg_tasks_qs = Task.objects.filter(
                    activity__phase__village_id__in=descendant_village_ids
                )
                total_tasks = agg_tasks_qs.count()
                done_tasks = agg_tasks_qs.filter(status=Task.COMPLETED).count()
                villages_with_priorities = descendant_villages.exclude(
                    identified_priority__isnull=True
                ).count()
                context["planning_status"] = {
                    "current_phase": None,
                    "current_activity": None,
                    "current_task": None,
                    "completed": round(float(done_tasks) * 100 / float(total_tasks), 2) if total_tasks else '-',
                    "priorities_identified": f"{villages_with_priorities}/{village_count}" if village_count else "-",
                    "village_development_plan_date": "",
                    "facilitator": "",
                }

            # Attach aggregated village_count + total_population to each direct
            # child by bucketing every descendant village under the child whose
            # subtree it sits in. A single parent map over the subtree avoids
            # per-child queries.
            parent_map = dict(
                AdministrativeLevel.objects.filter(id__in=level_ids)
                .values_list('id', 'parent_id')
            )
            children = list(admin_level.children.all().order_by('name'))
            direct_child_ids = {c.id for c in children}
            child_stats = {
                cid: {"village_count": 0, "total_population": 0}
                for cid in direct_child_ids
            }
            for v in descendant_villages.values('parent_id', 'total_population'):
                cur = v['parent_id']
                while cur is not None and cur not in direct_child_ids:
                    cur = parent_map.get(cur)
                if cur is not None:
                    child_stats[cur]["village_count"] += 1
                    child_stats[cur]["total_population"] += v['total_population'] or 0
            for child in children:
                s = child_stats.get(child.id, {"village_count": 0, "total_population": 0})
                child.computed_village_count = s["village_count"]
                child.computed_total_population = s["total_population"]
            context["children_list"] = children

            context["investments"] = Investment.objects.filter(
                administrative_level_id__in=descendant_village_ids
            ).select_related('administrative_level', 'funded_by').annotate(
                status_order=Case(
                    When(project_status=Investment.NOT_FUNDED, then=0),
                    When(project_status=Investment.PAUSED, then=1),
                    When(project_status=Investment.FUNDED, then=2),
                    When(project_status=Investment.IN_PROGRESS, then=3),
                    When(project_status=Investment.COMPLETED, then=4),
                    output_field=IntegerField(),
                )
            ).order_by('status_order', 'ranking')

        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")

        context['children_coordinates'] = json.dumps(self.object.get_villages_coordinates())

        package = Package.objects.get_active_cart(user=self.request.user)
        context["cart_items_id"] = [inv.id for inv in package.funded_investments.all()]

        return context

    def _get_planning_cycle(self):
        phases = list()
        admin_level = self.object
        for phase in admin_level.phases.all().order_by("order"):
            phase_node = {
                "id": phase.id,
                "name": phase.name,
                "order": phase.order,
                "activities": list(),
            }
            activities_status = None
            for activity in phase.activities.all().order_by("order"):
                activity_node = {
                    "id": activity.id,
                    "name": activity.name,
                    "order": activity.order,
                    "tasks": list(),
                }
                tasks_status = None
                for task in activity.tasks.all().order_by("order"):
                    task_node = {
                        "id": task.id,
                        "name": task.name,
                        "order": task.order,
                        "status": task.status,
                    }
                    activity_node["tasks"].append(task_node)
                    if tasks_status is None:
                        tasks_status = task.status
                    if task.status != Task.ERROR:
                        if tasks_status == Task.COMPLETED and task.status == Task.IN_PROGRESS:
                            tasks_status = Task.IN_PROGRESS
                    else:
                        tasks_status = Task.ERROR
                activity_node["status"] = tasks_status
                phase_node["activities"].append(activity_node)
                if activities_status is None:
                    activities_status = tasks_status
                if activity_node["status"] != Task.ERROR:
                    if activities_status == Task.COMPLETED and activity_node["status"] == Task.IN_PROGRESS:
                        activities_status = Task.IN_PROGRESS
                else:
                    activities_status = Task.ERROR
            phase_node["status"] = activities_status
            phases.append(phase_node)
        return phases

    def _get_development_plan(self, phases):
        phase = next((phase for phase in phases if phase['order'] == 3), None)
        if phase is not None:
            activity = next((activity for activity in phase['activities'] if activity['order'] == 2), None)
            if activity is not None:
                task = next((task for task in activity['tasks'] if task['order'] == 1), None)
                if task is not None:
                    task_obj = Task.objects.get(id=task['id'])
                    return task_obj.attachments.filter(
                        Q(type__icontains='pdf') |
                        Q(type__icontains='Document')
                    ).first()
        return None

    def __get_upper_services_infrastructure(self, parent):
        children = parent.children.all()
        final_resp = dict()
        final_total_ids = list()
        for child in children:
            grandchildren = child.children.all()
            if grandchildren:
                base_resp, total_ids = self.__get_upper_services_infrastructure(child)
            else:
                base_resp = child.infrastructure
                if base_resp is not None:
                    for key, value in base_resp.items():
                        for k, v in base_resp[key].items():
                            if base_resp[key][k]:
                                base_resp[key][k] = {'ids_true': [child.id]}
                            else:
                                base_resp[key][k] = {'ids_true': []}
                            total_ids = [child.id]
                else:
                    final_total_ids += [child.id]
                    print('###')
                    print("Village without infrastructure: ", child.id)
                    print('###')

            if base_resp is not None:
                for key, value in base_resp.items():
                    if key in final_resp:
                        for i, v in base_resp[key].items():
                            if i in final_resp[key]:
                                final_resp[key][i]['ids_true'] += base_resp[key][i]['ids_true']
                            else:
                                final_resp[key][i] = base_resp.key.i
                            final_total_ids += total_ids
                    else:
                        final_resp[key] = base_resp[key]
                        final_total_ids += total_ids

        return final_resp, final_total_ids


class AdministrativeLevelInfrastructureDistributionDetailView(
    PageMixin, LoginRequiredApproveRequiredMixin, TemplateView
):
    template_name = 'administrative_level/infrastructure.html'
    category = None

    def get_context_data(self, **kwargs):
        obj = AdministrativeLevel.objects.get(id=self.kwargs['pk'])
        context = super().get_context_data(**kwargs)
        context['title'] = "{} {}".format(obj.type, obj.name)
        context['villages_that_has_it'], villages = self.__get_villages_services_infrastructure(obj)
        context['villages_that_dont_has_it'] = [village for village in villages if
                                                village not in context['villages_that_has_it']]
        context['infrastructure'] = self.kwargs['infrastructure']
        context['category'] = self.category
        return context

    def __get_villages_services_infrastructure(self, parent):
        children = parent.children.all()
        has_it = list()
        villages = list()
        for child in children:
            grandchildren = child.children.all()
            if grandchildren:
                has_it_aux, dont_has_it_aux = self.__get_villages_services_infrastructure(child)
                has_it += has_it_aux
                villages += dont_has_it_aux
            else:
                if child.infrastructure is not None:
                    has_it_bool = False
                    for key, value in child.infrastructure.items():
                        for k, v in child.infrastructure[key].items():
                            if k == self.kwargs['infrastructure'] and child.infrastructure[key][k] == True:
                                has_it_bool = True
                                if self.category is None:
                                    self.category = key
                    if has_it_bool:
                        has_it.append(child)
                villages.append(child)

        return has_it, villages


class CommunePrioritiesMixin:

    def _get_params(self):
        """Unified method to get params from GET or POST for HTMX requests."""
        if self.request.htmx and self.request.method == 'POST':
            return self.request.POST
        return self.request.GET

    def _get_priorities_filters(self):
        context = {}
        params = self._get_params()

        context["categories"] = Category.objects.all()
        if params.get("category-filter"):
            context["sectors"] = Sector.objects.filter(
                category=params["category-filter"]
            )
        else:
            context["sectors"] = Sector.objects.none()

        context["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {"id": "endorsed_by_pastoralist", "name": _("Endorsed by ethnic minorities")},
        ]

        context["funding_statuses"] = [
            {"id": Investment.FUNDED, "name": _("Funded")},
            {"id": Investment.NOT_FUNDED, "name": _("Not Funded")},
        ]

        package = Package.objects.get_active_cart(user=self.request.user)
        context["cart_items_id"] = [inv.id for inv in package.funded_investments.all()]
        return context

    def _get_queryset(self, queryset):
        empty = ["", None]
        params = self._get_params()

        if params.get("category-filter") not in empty:
            queryset = queryset.filter(sector__category__id=params["category-filter"])

        if params.get("sector-filter") not in empty:
            queryset = queryset.filter(sector__id=params["sector-filter"])

        if params.get("subpopulation-filter") not in empty:
            queryset = queryset.filter(**{params["subpopulation-filter"]: True})

        climate_val = params.get("climate-contribution-filter", "")
        if climate_val == "True":
            queryset = queryset.filter(climate_contribution=True)
        elif climate_val == "False":
            queryset = queryset.filter(climate_contribution=False)

        if params.get("funding-status-filter") not in empty:
            if params["funding-status-filter"] == Investment.FUNDED:
                queryset = queryset.filter(
                    project_status__in=[
                        Investment.FUNDED, Investment.IN_PROGRESS, Investment.PAUSED, Investment.COMPLETED
                    ]
                )
            else:
                queryset = queryset.filter(project_status=Investment.NOT_FUNDED)

        return queryset

    def _build_investments_qs(self, admin_level):
        """QuerySet base de investments de la commune, con filtros aplicados."""
        base_qs = Investment.objects.filter(
            administrative_level__in=Subquery(
                AdministrativeLevel.objects.filter(
                    parent__parent=admin_level
                ).values_list("id", flat=True)
            )
        ).select_related("sector__category", "administrative_level__parent")
        return self._get_queryset(base_qs)

    def _build_priorities_context(self, admin_level):
        """Contexto completo para priorities.html."""
        context = self._get_priorities_filters()
        context["investments"] = self._build_investments_qs(admin_level)

        params = self._get_params()
        context["query_strings_raw"] = {
            k: v[0] if isinstance(v, list) and v else v
            for k, v in params.lists()
        }

        context["commune_post_url"] = reverse(
            "administrativelevels:commune_detail",
            args=[admin_level.pk],
        )

        context["priorities_partial_url"] = reverse(
            "administrativelevels:commune_priorities_partial",
            args=[admin_level.pk],
        )
        return context


class CantonPrioritiesMixin:

    def _get_params(self):
        """Unified method to get params from GET or POST for HTMX requests."""
        if self.request.htmx and self.request.method == 'POST':
            return self.request.POST
        return self.request.GET

    def _get_priorities_filters(self):
        context = {}
        params = self._get_params()

        context["categories"] = Category.objects.all()
        if params.get("category-filter"):
            context["sectors"] = Sector.objects.filter(
                category=params["category-filter"]
            )
        else:
            context["sectors"] = Sector.objects.none()

        context["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {"id": "endorsed_by_pastoralist", "name": _("Endorsed by ethnic minorities")},
        ]

        context["priorities"] = [
            {"id": 1, "name": _("Priority 1")},
            {"id": 2, "name": _("Priorities 1 and 2")},
            {"id": 3, "name": _("All priorities")}
        ]

        package = Package.objects.get_active_cart(user=self.request.user)
        context["cart_items_id"] = [inv.id for inv in package.funded_investments.all()]
        return context

    def _get_queryset(self, queryset):
        empty = ["", None]
        params = self._get_params()

        if params.get("category-filter") not in empty:
            queryset = queryset.filter(sector__category__id=params["category-filter"])

        if params.get("sector-filter") not in empty:
            queryset = queryset.filter(sector__id=params["sector-filter"])

        if params.get("subpopulation-filter") not in empty:
            queryset = queryset.filter(**{params["subpopulation-filter"]: True})

        if params.get("priorities-filter") not in empty:
            priorities = [1]
            if params["priorities-filter"] in ["2", "3"]:
                priorities = [1, 2]
            if params["priorities-filter"] == "3":
                pass
            else:
                queryset = queryset.filter(ranking__in=priorities)

        climate_val = params.get("climate-contribution-filter", "")
        if climate_val == "True":
            queryset = queryset.filter(climate_contribution=True)
        elif climate_val == "False":
            queryset = queryset.filter(climate_contribution=False)

        return queryset

    def _build_investments_qs(self, admin_level):
        """QuerySet base de investments del canton, con filtros aplicados."""
        base_qs = Investment.objects.filter(
            administrative_level__parent=admin_level,
            administrative_level__type=AdministrativeLevel.VILLAGE,
        ).select_related(
            "administrative_level",
            "sector__category",
            "funded_by",
        ).annotate(
            funding_order=Case(
                When(project_status=Investment.NOT_FUNDED, then=Value(0)),
                When(project_status=Investment.PAUSED, then=Value(1)),
                When(project_status=Investment.FUNDED, then=Value(2)),
                When(project_status=Investment.IN_PROGRESS, then=Value(3)),
                When(project_status=Investment.COMPLETED, then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            ),
            total_beneficiaries=Sum('administrative_level__total_population')
        ).order_by("funding_order", "ranking", "administrative_level__name")
        return self._get_queryset(base_qs)

    def _build_priorities_context(self, admin_level):
        """Contexto completo para priorities.html del canton."""
        context = self._get_priorities_filters()
        context["all_canton_priorities"] = self._build_investments_qs(admin_level)

        params = self._get_params()
        context["query_strings_raw"] = {
            k: v[0] if isinstance(v, list) and v else v
            for k, v in params.lists()
        }

        context["canton_post_url"] = reverse(
            "administrativelevels:canton_detail",
            args=[admin_level.pk],
        )

        context["priorities_partial_url"] = reverse(
            "administrativelevels:canton_priorities_partial",
            args=[admin_level.pk],
        )
        return context


class CommuneDetailView(PageMixin, GRMMixin, LoginRequiredApproveRequiredMixin, CommunePrioritiesMixin, DetailView):
    model = AdministrativeLevel
    template_name = "commune/commune_detail.html"
    active_level1 = "administrative_levels"

    def __init__(self):
        super().__init__()
        self.__investment_repository = DbInvestmentRepository()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'cart-toggle' in request.POST:
            investment = Investment.objects.get(id=request.POST['cart-toggle'])
            if investment.project_status == Investment.NOT_FUNDED:
                package = Package.objects.get_active_cart(user=self.request.user)
                if package.funded_investments.filter(id=investment.id).exists():
                    package.funded_investments.remove(investment)
                    track_user_activity(request, 'RemoveInvestmentInPackage')
                else:
                    package.funded_investments.add(investment)
                    track_user_activity(request, 'AddInvestmentInPackage')

            if request.headers.get('x-hx-request'):
                context = self.get_context_data(**kwargs)
                return self.render_to_response(context)
            return super().get(request, *args, **kwargs)

        obj = self.get_object()
        url = reverse("administrativelevels:commune_detail", args=[obj.id])
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if (
                    key in request.POST
                    and value != request.POST[key]
                    and request.POST[key] != ""
            ):
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop("csrfmiddlewaretoken")
        if "reset-hidden" in post_dict and post_dict["reset-hidden"] == "true":
            return redirect(url)

        for key, value in request.POST.items():
            if value == "":
                post_dict.pop(key)
        final_querystring.update(post_dict)
        if final_querystring:
            url = "{}?{}".format(url, urlencode(final_querystring))
        return redirect(url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        images_extensions_query = Q()
        for ext in IMAGE_EXTENSIONS:
            images_extensions_query |= Q(url__icontains=ext)

        if "object" in context:
            context["title"] = "%s %s" % (_(context['object'].type), context['object'].name)
            if context["object"].is_village():
                context["investments"] = self.__investment_repository.find_by_criteria(
                    InvestmentCriteria(administrative_level=self.object))
        admin_level = context.get("object")

        context["context_object_name"] = admin_level.type.lower()

        # Get images with priority on process_moment (like village_detail)
        # For Commune, include images from child cantons and grandchild villages
        child_cantons = AdministrativeLevel.objects.filter(
            parent=admin_level,
        ).filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.CANTON)
        )
        descendant_villages = AdministrativeLevel.objects.filter(
            parent__in=child_cantons,
        ).filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
        )
        all_descendants = AdministrativeLevel.objects.filter(
            Q(id=admin_level.id) |
            Q(id__in=child_cantons) |
            Q(id__in=descendant_villages)
        )

        images_number = 5
        completed = Attachment.objects.filter(
            Q(adm__in=all_descendants) |
            Q(task__activity__phase__village__in=all_descendants),
            process_moment=Attachment.COMPLETED_INFRASTRUCTURE
        ).filter(images_extensions_query)[:3]

        in_progress = []
        if not completed:
            in_progress = Attachment.objects.filter(
                Q(adm__in=all_descendants) |
                Q(task__activity__phase__village__in=all_descendants),
                process_moment=Attachment.INFRASTRUCTURE_IN_PROGRESS
            ).filter(images_extensions_query)[:1]

        community = Attachment.objects.filter(
            Q(adm__in=all_descendants) |
            Q(task__activity__phase__village__in=all_descendants),
            process_moment=Attachment.COMMUNITY_PROCESS
        ).filter(images_extensions_query)[:(images_number - len(completed) - len(in_progress))]

        images = list(completed) + list(in_progress) + list(community)

        context["images_data"] = {
            "images": images,
            "exists_at_least_image": len(images) != 0,
            "first_image": images[0] if len(images) > 0 else None,
        }

        # Aggregate population data from descendant villages
        population_aggregation = descendant_villages.aggregate(
            agg_total_population=Coalesce(Sum('total_population'), 0),
            agg_population_men=Coalesce(Sum('population_men'), 0),
            agg_population_women=Coalesce(Sum('population_women'), 0),
            agg_population_young=Coalesce(Sum('population_young'), 0),
            agg_population_elder=Coalesce(Sum('population_elder'), 0),
            agg_population_handicap=Coalesce(Sum('population_handicap'), 0),
            agg_population_agriculturist=Coalesce(Sum('population_agriculturist'), 0),
            agg_population_pastoralist=Coalesce(Sum('population_pastoralist'), 0),
            agg_population_minorities=Coalesce(Sum('population_minorities'), 0),
            agg_total_estimated_cost=Coalesce(Sum('investments__estimated_cost'), 0),
        )
        context["population"] = {
            "total": population_aggregation['agg_total_population'],
            "men": population_aggregation['agg_population_men'],
            "women": population_aggregation['agg_population_women'],
            "young": population_aggregation['agg_population_young'],
            "elder": population_aggregation['agg_population_elder'],
            "handicap": population_aggregation['agg_population_handicap'],
            "agriculturist": population_aggregation['agg_population_agriculturist'],
            "pastoralist": population_aggregation['agg_population_pastoralist'],
            "minorities": population_aggregation['agg_population_minorities'],
            "total_estimated_cost": population_aggregation['agg_total_estimated_cost'],
            "village_count": descendant_villages.count(),
            "canton_count": child_cantons.count(),
        }

        context["villages"] = AdministrativeLevel.objects.filter(
            parent__parent=admin_level
        ).annotate(
            total_estimated_cost=Coalesce(
                Sum('investments__estimated_cost'), 0
            ),
            total_founded=Coalesce(
                Sum(
                    Case(
                        When(investments__project_status=Investment.FUNDED, then=F('investments__estimated_cost')),
                        default=0,
                        output_field=IntegerField(),
                    )
                ), 0
            )
        ).annotate(
            per_capita_invested=Case(
                When(total_population__gt=0, then=F('total_founded') / F('total_population')),
                default=0,
                output_field=IntegerField(),
            ),
            per_capita_required=Case(
                When(total_population__gt=0, then=F('total_estimated_cost') / F('total_population')),
                default=0,
                output_field=IntegerField(),
            )
        )

        context["subprojects"] = Investment.objects.filter(
            administrative_level__in=Subquery(
                AdministrativeLevel.objects.filter(
                    parent__parent=admin_level
                ).values_list('id', flat=True)
            )
        ).exclude(project_status=Investment.NOT_FUNDED)

        # Add planning status information
        tasks_qs = Task.objects.filter(activity__phase__village=admin_level)
        current_task = admin_level.get_current_task()
        current_activity = current_task.activity if current_task else None
        current_phase = current_activity.phase if current_activity else None

        task_number = tasks_qs.count()
        tasks_done = tasks_qs.filter(status=Task.COMPLETED).count()
        context["planning_status"] = {
            "current_phase": current_phase,
            "current_activity": current_activity,
            "current_task": current_task,
            "completed": round(float(tasks_done) * 100 / float(task_number), 2) if task_number != 0 else '-',
            "priorities_identified": context["object"].identified_priority,
            "village_development_plan_date": "",
            "facilitator": "",
        }

        phases = self._get_planning_cycle()
        context["development_plan"] = self._get_development_plan(phases)

        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")
        context['children_coordinates'] = json.dumps(self.object.get_villages_coordinates())

        context.update(self._build_priorities_context(admin_level))

        return context

    def _get_planning_cycle(self):
        phases = list()
        admin_level = self.object

        # Optimize phases query with selective fields and prefetch
        phases_qs = admin_level.phases.all().only(
            "id", "name", "order"
        ).prefetch_related(
            Prefetch(
                "activities",
                queryset=Activity.objects.all().only("id", "name", "order", "phase_id").prefetch_related(
                    Prefetch(
                        "tasks",
                        queryset=Task.objects.all().only("id", "name", "order", "status", "activity_id")
                    )
                )
            )
        )

        for phase in phases_qs:
            phase_node = {
                "id": phase.id,
                "name": phase.name,
                "order": phase.order,
                "activities": list(),
            }
            activities_status = None
            for activity in phase.activities.all():
                activity_node = {
                    "id": activity.id,
                    "name": activity.name,
                    "order": activity.order,
                    "tasks": list(),
                }
                tasks_status = None
                for task in activity.tasks.all():
                    task_node = {
                        "id": task.id,
                        "name": task.name,
                        "order": task.order,
                        "status": task.status,
                    }
                    activity_node["tasks"].append(task_node)

                    t_status = task.status
                    if tasks_status is None:
                        tasks_status = t_status

                    if t_status == Task.ERROR:
                        tasks_status = Task.ERROR
                    elif tasks_status == Task.COMPLETED and t_status == Task.IN_PROGRESS:
                        tasks_status = Task.IN_PROGRESS

                activity_node["status"] = tasks_status
                phase_node["activities"].append(activity_node)

                if activities_status is None:
                    activities_status = tasks_status

                if activity_node["status"] == Task.ERROR:
                    activities_status = Task.ERROR
                elif activities_status == Task.COMPLETED and activity_node["status"] == Task.IN_PROGRESS:
                    activities_status = Task.IN_PROGRESS

            phase_node["status"] = activities_status
            phases.append(phase_node)
        return phases

    def _get_development_plan(self, phases):
        phase = next((phase for phase in phases if phase['order'] == 3), None)
        if phase is not None:
            activity = next((activity for activity in phase['activities'] if activity['order'] == 2), None)
            if activity is not None:
                task = next((task for task in activity['tasks'] if task['order'] == 1), None)
                if task is not None:
                    task_obj = Task.objects.get(id=task['id'])
                    return task_obj.attachments.filter(
                        Q(type__icontains='pdf') |
                        Q(type__icontains='Document')
                    ).first()
        return None


class CommunePrioritiesPartialView(LoginRequiredApproveRequiredMixin, CommunePrioritiesMixin, DetailView):
    model = AdministrativeLevel
    template_name = "commune/tabs/priorities.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_priorities_context(self.object))
        return context


class CantonPrioritiesPartialView(LoginRequiredApproveRequiredMixin, CantonPrioritiesMixin, DetailView):
    model = AdministrativeLevel
    template_name = "canton/tabs/priorities.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._build_priorities_context(self.object))
        return context


class CantonDetailView(PageMixin, GRMMixin, LoginRequiredApproveRequiredMixin, CantonPrioritiesMixin, DetailView):
    model = AdministrativeLevel
    template_name = "canton/canton_detail.html"
    active_level1 = "administrative_levels"

    def __init__(self):
        super().__init__()
        self.__investment_repository = DbInvestmentRepository()

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if 'cart-toggle' in request.POST:
            investment = Investment.objects.get(id=request.POST['cart-toggle'])
            if investment.project_status == Investment.NOT_FUNDED:
                package = Package.objects.get_active_cart(user=self.request.user)
                if package.funded_investments.filter(id=investment.id).exists():
                    package.funded_investments.remove(investment)
                    track_user_activity(request, 'RemoveInvestmentInPackage')
                else:
                    package.funded_investments.add(investment)
                    track_user_activity(request, 'AddInvestmentInPackage')

            if request.headers.get('x-hx-request'):
                context = self.get_context_data(**kwargs)
                return self.render_to_response(context)
            return super().get(request, *args, **kwargs)

        obj = self.get_object()
        url = reverse("administrativelevels:canton_detail", args=[obj.id])
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if (
                    key in request.POST
                    and value != request.POST[key]
                    and request.POST[key] != ""
            ):
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop("csrfmiddlewaretoken")
        if "reset-hidden" in post_dict and post_dict["reset-hidden"] == "true":
            return redirect(url)

        for key, value in request.POST.items():
            if value == "":
                post_dict.pop(key)
        final_querystring.update(post_dict)
        if final_querystring:
            url = "{}?{}".format(url, urlencode(final_querystring))
        return redirect(url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        canton = self.object

        context["title"] = f"{_(canton.type)} {canton.name}"
        context["context_object_name"] = canton.type.lower()

        # --- Delegate aggregation to the service layer ---
        summary_service = CantonSummaryService(canton)

        images = summary_service.get_carousel_images()
        context["images_data"] = {
            "images": images,
            "exists_at_least_image": bool(images),
            "first_image": images[0] if images else None,
        }

        # Always use aggregated population
        context["canton_population"] = summary_service.get_population_aggregates()

        # New: Villages Summary card
        context["villages_summary"] = summary_service.get_villages_summary()

        # Keep existing villages queryset for the Villages tab
        context["villages"] = AdministrativeLevel.objects.filter(
            parent=canton,
        ).filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
        ).annotate(
            total_estimated_cost=Coalesce(Sum('investments__estimated_cost'), 0),
            total_founded=Coalesce(
                Sum(Case(
                    When(investments__project_status=Investment.FUNDED,
                         then=F('investments__estimated_cost')),
                    default=0,
                    output_field=IntegerField(),
                )), 0
            )
        )

        context.update(self._build_priorities_context(canton))
        context["investments"] = self._get_queryset(
            Investment.objects.filter(
                project_status=Investment.NOT_FUNDED,
                administrative_level__parent=canton,
            ).filter(
                AdministrativeLevel.type_filter_q(
                    AdministrativeLevel.VILLAGE,
                    field="administrative_level__type",
                ),
            ).only(
                "id", "ranking", "title", "description",
                "endorsed_by_youth", "endorsed_by_women",
                "endorsed_by_pastoralist", "endorsed_by_agriculturist",
                "estimated_cost", "project_status", "sector", "administrative_level",
            )
        )

        context["subprojects"] = Investment.objects.filter(
            administrative_level__parent=canton,
        ).filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.VILLAGE,
                field="administrative_level__type",
            ),
        ).exclude(project_status=Investment.NOT_FUNDED).only(
            "id", "ranking", "title", "description",
            "endorsed_by_youth", "endorsed_by_women",
            "endorsed_by_pastoralist", "endorsed_by_agriculturist",
            "estimated_cost", "project_status", "funded_by",
            "climate_contribution", "climate_contribution_text",
            "administrative_level",
        )
        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")
        context['children_coordinates'] = json.dumps(self.object.get_villages_coordinates())

        return context

    def _get_planning_cycle(self):
        phases = list()
        admin_level = self.object

        # Optimize phases query with selective fields and prefetch
        phases_qs = admin_level.phases.all().only(
            "id", "name", "order"
        ).prefetch_related(
            Prefetch(
                "activities",
                queryset=Activity.objects.all().only("id", "name", "order", "phase_id").prefetch_related(
                    Prefetch(
                        "tasks",
                        queryset=Task.objects.all().only("id", "name", "order", "status", "activity_id")
                    )
                )
            )
        )

        for phase in phases_qs:
            phase_node = {
                "id": phase.id,
                "name": phase.name,
                "order": phase.order,
                "activities": list(),
            }
            activities_status = None
            for activity in phase.activities.all():
                activity_node = {
                    "id": activity.id,
                    "name": activity.name,
                    "order": activity.order,
                    "tasks": list(),
                }
                tasks_status = None
                for task in activity.tasks.all():
                    task_node = {
                        "id": task.id,
                        "name": task.name,
                        "order": task.order,
                        "status": task.status,
                    }
                    activity_node["tasks"].append(task_node)

                    t_status = task.status
                    if tasks_status is None:
                        tasks_status = t_status

                    if t_status == Task.ERROR:
                        tasks_status = Task.ERROR
                    elif tasks_status == Task.COMPLETED and t_status == Task.IN_PROGRESS:
                        tasks_status = Task.IN_PROGRESS

                activity_node["status"] = tasks_status
                phase_node["activities"].append(activity_node)

                if activities_status is None:
                    activities_status = tasks_status

                if activity_node["status"] == Task.ERROR:
                    activities_status = Task.ERROR
                elif activities_status == Task.COMPLETED and activity_node["status"] == Task.IN_PROGRESS:
                    activities_status = Task.IN_PROGRESS

            phase_node["status"] = activities_status
            phases.append(phase_node)
        return phases

    def _get_development_plan(self, phases):
        phase = next((phase for phase in phases if phase['order'] == 3), None)
        if phase is not None:
            activity = next((activity for activity in phase['activities'] if activity['order'] == 2), None)
            if activity is not None:
                task = next((task for task in activity['tasks'] if task['order'] == 1), None)
                if task is not None:
                    task_obj = Task.objects.get(id=task['id'])
                    return task_obj.attachments.filter(
                        Q(type__icontains='pdf') |
                        Q(type__icontains='Document')
                    ).first()
        return None



class CantonPlanningSummaryView(LoginRequiredApproveRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "canton/tabs/planning_cycle.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        canton = self.get_object()
        planning_service = CantonPlanningService(canton)
        context["planning_summary"] = planning_service.get_summary()
        return context


class CantonMapView(LoginRequiredApproveRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "canton/tabs/map_tab.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        canton = self.get_object()
        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")

        map_service = CantonMapService(canton)
        villages_map_data = map_service.get_villages_geo_data()
        context["villages_map_data_json"] = json.dumps(villages_map_data, default=str)
        return context


class ProjectListView(PageMixin, IsInvestorMixin, ListView):
    queryset = Project.objects.all()
    template_name = 'project/list.html'
    context_object_name = "projects"
    title = _("Projects")
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, *args, object_list=None, **kwargs):
        queryset = object_list if object_list is not None else self.object_list

        context = super().get_context_data(object_list=queryset, **kwargs)

        object_name = self.get_context_object_name(queryset)
        if object_name in context:
            context[object_name] = context[object_name].annotate(
                investments_count=Count('packages__funded_investments'))
            context[object_name] = context[object_name].annotate(
                investments_total=Sum('packages__funded_investments__estimated_cost'))
            context['total_mount_invested'] = context[object_name].aggregate(Sum('investments_total'))[
                                                  'investments_total__sum'] or 0

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(organization=self.request.user.organization)
        return queryset


class ProjectDetailView(PageMixin, IsInvestorMixin, BaseFormView, DetailView):
    queryset = Project.objects.all()
    template_name = 'project/detail.html'
    context_object_name = "project"
    form_class = ProjectForm
    investment_form_class = UpdateInvestmentForm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if 'image_input' in request.FILES:
            try:
                investment = Investment.objects.filter(
                    funded_by__id=self.object.id,
                ).get(id=request.POST['investment'])
                succeeded, new_attachment = Attachment.investment_upload(
                    investment=investment,
                    image=request.FILES.get('image_input')
                )
                if succeeded:
                    messages.add_message(request, messages.SUCCESS, _("Investment updated."))
                    track_user_activity(request, 'UploadInvestmentFile')
                else:
                    import logging
                    logging.getLogger(__name__).error(
                        "investment_upload returned False: %s", new_attachment
                    )
                    messages.add_message(request, messages.ERROR, _("Investment could not be updated."))
            except Exception as exc:
                import logging
                logging.getLogger(__name__).exception("Image upload error: %s", exc)
                messages.add_message(request, messages.ERROR, _("Investment could not be updated."))
            return super().get(request, *args, **kwargs)

        if 'investment' in request.POST:
            investment = Investment.objects.get(id=request.POST['investment'])
            investment_form = self.investment_form_class(
                instance=investment, data=request.POST, files=request.FILES
            )
            if investment_form.is_valid():
                investment_form.save()
                messages.add_message(request, messages.SUCCESS, _("Investment updated."))
                track_user_activity(request, 'InvestmentUpdated')
            else:
                messages.add_message(request, messages.ERROR, _("Investment could not be updated."))
            return super().get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.title = self.object.name
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        project = self.object
        context["packages"] = project.packages.all().order_by("created_date")
        inv_ids = list()
        for package in context["packages"]:
            inv_ids += package.funded_investments.all().values_list("id", flat=True)
        context["investments"] = Investment.objects.filter(funded_by__id=self.object.id).exclude(
            packages__in=Subquery(
                Package.objects.filter(
                    user=self.request.user,
                    status__in=[Package.PENDING_SUBMISSION]
                ).values_list("id")
            )
        ).exclude(
            # Exclure les investissements individuellement rejetés dans un paquet
            packagefundedinvestment__status=PackageFundedInvestment.REJECTED
        )
        context["project_status"] = Investment.PROJECT_STATUS_CHOICES
        context["organization"] = project.owner.organization
        context["project"] = project

        if context["organization"] is not None:
            user_qs = context["organization"].users.all().values_list("id")
            investments_qs = Investment.objects.filter(
                packages__user__id__in=Subquery(user_qs)
            ).exclude(
                packages__in=Subquery(
                    Package.objects.filter(
                        user=self.request.user,
                        status__in=[Package.PENDING_SUBMISSION]
                    ).values_list("id")
                )
            )
            context["organization"].total_investments = investments_qs.count()
            context["organization"].total_investments_amount = investments_qs.aggregate(
                Sum("estimated_cost")
            )["estimated_cost__sum"]

        context["datatable_config"] = get_datatable_config()
        context["datatable_config"]["responsive"] = "true"

        context["investments_datatable_config"] = context["datatable_config"].copy()
        context["investments_datatable_config"]["pageLength"] = 500
        context["investments_datatable_config"]["columnDefs"] = [
            {"responsivePriority": 1, "targets": 0},
            {"responsivePriority": 2, "targets": 1},
            {"responsivePriority": 3, "targets": 2},
            {"responsivePriority": 4, "targets": 3},
            {"responsivePriority": 5, "targets": 4},
            {"responsivePriority": 6, "targets": 5},
            {"responsivePriority": 7, "targets": 6},
            {"responsivePriority": 8, "targets": 7},
            {"responsivePriority": 9, "targets": 8},
        ]

        context["packages_datatable_config"] = context["datatable_config"].copy()
        context["packages_datatable_config"]["columnDefs"] = [
            {"responsivePriority": 1, "targets": 0},
            {"responsivePriority": 2, "targets": 1},
            {"responsivePriority": 3, "targets": 2},
            {"responsivePriority": 4, "targets": 3},
        ]

        # Carte Mapbox : coordonnées des investissements du projet
        import json as _json
        try:
            from cosomis.settings import MAPBOX_ACCESS_TOKEN as _MAPBOX_TOKEN
        except Exception:
            _MAPBOX_TOKEN = ""
        context["mapbox_access_token"] = _MAPBOX_TOKEN or ""
        investments_with_coords = list(
            context["investments"].filter(
                latitude__isnull=False,
                longitude__isnull=False,
            ).values(
                'id', 'title', 'latitude', 'longitude',
                'sector__name', 'sector__category__name',
                'physical_execution_rate', 'project_status',
                'description',
                'administrative_level__id',
                'administrative_level__name',
                'administrative_level__parent__name',
                'administrative_level__parent__parent__name',
                'administrative_level__parent__parent__parent__name',
                'administrative_level__parent__parent__parent__parent__name',
            )
        )
        # Ajouter les URLs d'images pour chaque investissement
        from investments.models import Attachment as _Attachment
        _inv_ids = [i['id'] for i in investments_with_coords]
        _photos = (
            _Attachment.objects
            .filter(investment_id__in=_inv_ids, type=_Attachment.PHOTO)
            .values('investment_id', 'url')
        )
        _photos_map = {}
        for _p in _photos:
            _photos_map.setdefault(_p['investment_id'], []).append(_p['url'])
        for _inv in investments_with_coords:
            _inv['attachments'] = _photos_map.get(_inv['id'], [])
        context["investments_map_data"] = _json.dumps(investments_with_coords, default=str)

        return context

    def form_valid(self, form):
        form.save()
        messages.add_message(self.request, messages.SUCCESS, _("Project updated."))
        context = self.get_context_data()
        return self.render_to_response(context)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(organization=self.request.user.organization)
        return queryset

    def get_success_url(self):
        return reverse('administrativelevels:project-detail', kwargs={'pk': self.object.pk})


class ProjectCreateView(PageMixin, IsInvestorMixin, CreateView):
    template_name = 'project/create/index.html'
    form_class = ProjectForm
    title = _("Create Project")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'owner': self.request.user})
        return kwargs

    def get_success_url(self):
        # return reverse('administrativelevels:project-upload-investments', kwargs={'pk': self.object.pk})
        return reverse('administrativelevels:projects')


class BulkUploadInvestmentsView(PageMixin, AdminPermissionRequiredMixin, SingleObjectMixin, FormView):
    form_class = BulkUploadInvestmentsForm
    template_name = 'project/create/bulk_upload_investments.html'
    queryset = Project.objects.all()
    object = None

    def form_valid(self, form):
        self.object = form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'project': self.get_object()})
        return kwargs

    def get_success_url(self):
        return reverse('administrativelevels:project-detail', kwargs={'pk': self.object.pk})


# Class that looks for the file in static/investments/upload_manual.md transforms it in pdf and returns in pdf
class DownloadManualView(PageMixin, LoginRequiredApproveRequiredMixin, DetailView):

    def get(self, request, *args, **kwargs):
        md_url = request.build_absolute_uri(static('investments/upload_manual.md'))
        response = requests.get(md_url)
        md = response.text

        pdf = self.md_to_pdf(md)

        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="upload_manual.pdf"'
        return response

    def md_to_pdf(self, md):
        import markdown
        from xhtml2pdf import pisa
        import io

        # Convert Markdown to HTML
        html = markdown.markdown(md)

        # Create a file-like buffer to receive PDF data
        result = io.BytesIO()

        # Convert HTML to PDF
        pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result)

        # Check for errors
        if pisa_status.err:
            return None

        # Return the PDF data
        return result.getvalue()


# Attachments
class AttachmentListView(PageMixin, LoginRequiredApproveRequiredMixin, ListView):
    template_name = "attachments/attachments.html"
    context_object_name = "attachments"
    title = _("Gallery")
    paginate_by = 10
    model = Attachment

    filter_hierarchy = [
                           'task',
                           'activity',
                           'phase'
                       ] + [adm_type[0].lower() for adm_type in AdministrativeLevel.TYPE]

    def post(self, request, *args, **kwargs):
        url = reverse("administrativelevels:attachments")
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if (
                    key in request.POST
                    and value != request.POST[key]
                    and request.POST[key] != ""
            ):
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop("csrfmiddlewaretoken")
        if "reset-hidden" in post_dict and post_dict["reset-hidden"] == "true":
            return redirect(url)

        for key, value in request.POST.items():
            if value == "":
                post_dict.pop(key)
        final_querystring.update(post_dict)
        if final_querystring:
            url = "{}?{}".format(url, urlencode(final_querystring))
        return redirect(url)

    def get_context_data(self, **kwargs):
        context = super(AttachmentListView, self).get_context_data(**kwargs)

        regions_qs = AdministrativeLevel.objects.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.REGION)
        )
        context["regions"] = regions_qs
        # When the dataset has a single root (e.g. Benin = one "country" row),
        # the top-level dropdown is just decoration. Auto-select it server-side
        # and pre-load its prefectures so the modal starts at the next level.
        single_region = regions_qs.first() if regions_qs.count() == 1 else None
        context["single_region"] = single_region
        context["prefectures"] = (
            AdministrativeLevel.objects.filter(parent=single_region).filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.PREFECTURE)
            )
            if single_region
            else AdministrativeLevel.objects.none()
        )
        context['phases'] = Phase.objects.all().values_list('name', flat=True).distinct()

        # Use the dataset's own level names so the modal/chip labels read
        # "Country / Département / ... / Village" on Benin instead of the
        # Togo-flavoured fallback.
        adm_labels = AdministrativeLevel.get_filter_labels()
        context["adm_labels"] = adm_labels

        query_params: dict = self.request.GET

        context["filter_hierarchy_query_strings"] = self.build_filter_hierarchy()
        context["query_strings_raw"] = query_params.copy()
        context["query_strings_raw"].pop("page", None)
        babylong_query_params_list = [key + '=' + value for key, value in context["query_strings_raw"].items()]
        if babylong_query_params_list:
            context["babylong_query_params"] = '&' + '&'.join(babylong_query_params_list)

        context["type_links"] = self._build_type_links(query_params)
        context["active_filter_chips"] = self._build_active_chips(query_params, adm_labels, single_region)

        form = AttachmentFilterForm()

        paginator = self.__build_db_filter()

        context["no_results"] = paginator.count == 0
        context["current_language"] = translation.get_language()
        page_number = int(query_params.get("page", 1))
        context["attachments"] = paginator.get_page(page_number) if page_number <= paginator.num_pages else []
        context["form"] = form
        return context

    def get_template_names(self, *args, **kwargs):
        if self.request.htmx:
            return "attachments/_grid.html"
        else:
            return self.template_name

    def __build_db_filter(self) -> Paginator:
        query: QuerySet = self.get_queryset()

        query = query.order_by("created_date").annotate(
            process_order=Case(
                When(process_moment=Attachment.COMPLETED_INFRASTRUCTURE, then=Value(1)),
                When(process_moment=Attachment.INFRASTRUCTURE_IN_PROGRESS, then=Value(2)),
                When(process_moment=Attachment.COMMUNITY_PROCESS, then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        ).order_by("process_order")
        paginator = Paginator(query, 36)

        return paginator

    def build_filter_hierarchy(self):
        resp = {}

        def _build_filter_hierarchy(index, get_value):
            current_filter_level = self.filter_hierarchy[index]
            next_filter_level = self.filter_hierarchy[index + 1] if index + 1 < len(self.filter_hierarchy) else None
            if current_filter_level == "task":
                # task = Task.objects.get(id=int(get_value))
                resp[current_filter_level] = get_value
                resp[next_filter_level] = self.request.GET[next_filter_level]
            if current_filter_level == "activity":
                # activity = Activity.objects.get(id=int(get_value))
                resp[current_filter_level] = get_value
                resp[next_filter_level] = self.request.GET[next_filter_level]
            if current_filter_level == "phase":
                # phase = Phase.objects.filter(name=get_value)
                resp[current_filter_level] = get_value
                if next_filter_level in self.request.GET:
                    resp[next_filter_level] = int(self.request.GET[next_filter_level])
            if current_filter_level in [adm_type[0].lower() for adm_type in AdministrativeLevel.TYPE]:
                try:
                    adm_lvl = AdministrativeLevel.objects.get(id=int(self.request.GET[current_filter_level]))
                except:
                    adm_lvl = AdministrativeLevel.objects.get(id=int(get_value))
                resp[current_filter_level] = adm_lvl.id
                if hasattr(adm_lvl, "parent") and adm_lvl.parent is not None and len(self.filter_hierarchy) > index + 1:
                    resp[next_filter_level] = adm_lvl.parent.id

            if len(self.filter_hierarchy) > index + 1 and 'village' in self.request.GET and self.request.GET[
                'village'] is not None:
                return _build_filter_hierarchy(index + 1, resp[next_filter_level])
            return resp

        for idx, key_filter in enumerate(self.filter_hierarchy):
            if key_filter in self.request.GET and self.request.GET[key_filter] not in ['', None]:
                resp = _build_filter_hierarchy(idx, self.request.GET[key_filter])
                return json.dumps(resp)

    @staticmethod
    def _querystring_without(query_params, *keys_to_drop):
        clean = query_params.copy()
        for key in ("page",) + tuple(keys_to_drop):
            clean.pop(key, None)
        for key in list(clean.keys()):
            if clean.get(key) in ("", None):
                clean.pop(key, None)
        encoded = clean.urlencode()
        return "?" + encoded if encoded else "?"

    def _build_type_links(self, query_params):
        active = query_params.get("type") or ""
        if active not in (Attachment.PHOTO, Attachment.DOCUMENT):
            active = "all"

        base = self._querystring_without(query_params, "type")
        separator = "" if base == "?" else "&"
        return {
            "all": base,
            Attachment.PHOTO: f"{base}{separator}type={Attachment.PHOTO}",
            Attachment.DOCUMENT: f"{base}{separator}type={Attachment.DOCUMENT}",
            "active": active,
        }

    def _build_active_chips(self, query_params, adm_label_keys, single_region=None):
        chips = []
        single_region_id = str(single_region.id) if single_region else None

        attachment_type = query_params.get("type")
        if attachment_type in (Attachment.PHOTO, Attachment.DOCUMENT):
            label_map = {Attachment.PHOTO: _("Photo"), Attachment.DOCUMENT: _("Document")}
            chips.append({
                "key": "type",
                "label": "{}: {}".format(_("Type"), label_map[attachment_type]),
                "remove_url": self._querystring_without(query_params, "type"),
            })

        for key, prefix in adm_label_keys.items():
            value = query_params.get(key)
            if not value:
                continue
            if key == "region" and single_region_id and value == single_region_id:
                continue
            try:
                adm_lvl = AdministrativeLevel.objects.get(id=int(value))
                name = adm_lvl.name
            except (AdministrativeLevel.DoesNotExist, ValueError, TypeError):
                continue
            chips.append({
                "key": key,
                "label": "{}: {}".format(prefix, name),
                "remove_url": self._querystring_without(query_params, key),
            })

        phase_name = query_params.get("phase")
        if phase_name:
            chips.append({
                "key": "phase",
                "label": "{}: {}".format(_("Phase"), phase_name),
                "remove_url": self._querystring_without(query_params, "phase"),
            })

        for key, model, prefix in (
            ("activity", Activity, _("Activity")),
            ("task", Task, _("Task")),
            ("tasks", Task, _("Task")),
        ):
            value = query_params.get(key)
            if not value:
                continue
            try:
                instance = model.objects.get(id=int(value))
                name = instance.name
            except (model.DoesNotExist, ValueError, TypeError):
                continue
            chips.append({
                "key": key,
                "label": "{}: {}".format(prefix, name),
                "remove_url": self._querystring_without(query_params, key),
            })

        return chips

    def get_queryset(self):
        queryset = super().get_queryset()
        empty_list = ["", None]

        request_get = self.request.GET.copy()
        for filter_hierarchy in self.filter_hierarchy:
            if filter_hierarchy in request_get and request_get[filter_hierarchy] in [None, ""]:
                request_get.pop(filter_hierarchy)

        attachment_type = request_get.get("type")
        if attachment_type in (Attachment.PHOTO, Attachment.DOCUMENT):
            queryset = queryset.filter(type=attachment_type)

        if "tasks" in request_get and request_get["tasks"] not in empty_list:
            queryset = queryset.filter(
                task__id=request_get["tasks"]
            )
        elif "activities" in request_get and request_get["activities"] not in empty_list:
            queryset = queryset.filter(
                task__activity__id=request_get["activities"]
            )
        elif "phase" in request_get and request_get["phase"] not in empty_list:
            queryset = queryset.filter(
                task__activity__phase__name=request_get["phase"]
            )

        adm_lvls = [adm_name[0].lower() for adm_name in AdministrativeLevel.TYPE]
        adm_list = [adm_type for adm_type in adm_lvls if adm_type in request_get]
        adm_type = adm_list[0] if adm_list else None

        if adm_type and request_get[adm_type] not in empty_list:
            administrative_levels = AdministrativeLevel.objects.get(id=request_get[adm_type])
            descendants = administrative_levels.get_all_descendants()
            queryset = queryset.filter(adm__id__in=[decs.id for decs in descendants] + [administrative_levels.id])

        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset


@login_required
def attachment_download(self, adm_id: int, url: str):
    response = requests.get(url)
    if response.status_code == 200:
        content_disposition = response.headers.get("content-disposition")
        filename = url.split("/")[-1]
        if content_disposition is not None:
            try:
                fname = re.findall('filename="(.+)"', content_disposition)

                if len(fname) != 0:
                    filename = fname[0]
            except:
                pass

        response = HttpResponse(
            response.content, content_type=response.headers.get("content-type")
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    else:
        return HttpResponse("Failed to download the file.")


@login_required
def attachment_download_by_id(request, pk: int):
    attachment = Attachment.objects.get(pk=pk)
    url = attachment.url.split("?")[0]
    response = requests.get(url)
    if response.status_code != 200:
        return HttpResponse("Failed to download the file.", status=502)

    filename = url.split("/")[-1]
    content_disposition = response.headers.get("content-disposition")
    if content_disposition is not None:
        try:
            fname = re.findall('filename="(.+)"', content_disposition)
            if len(fname) != 0:
                filename = fname[0]
        except:
            pass

    out = HttpResponse(
        response.content, content_type=response.headers.get("content-type")
    )
    out["Content-Disposition"] = f'attachment; filename="{filename}"'
    return out


@login_required
def attachment_download_zip(self, adm_id: int):
    ids = self.GET.get("ids").split(",")

    buffer = BytesIO()
    zip_file = zipfile.ZipFile(buffer, "w")
    for id in ids:
        url = Attachment.objects.get(id=int(id)).url.split("?")[0]
        response = requests.get(url)
        if response.status_code == 200:
            content_disposition = response.headers.get("content-disposition")
            filename = url.split("/")[-1]
            if content_disposition is not None:
                try:
                    fname = re.findall('filename="(.+)"', content_disposition)

                    if len(fname) != 0:
                        filename = fname[0]
                except:
                    pass
        zip_file.writestr(filename, response.content)

    zip_file.close()

    response = HttpResponse(buffer.getvalue())
    response["Content-Type"] = "application/x-zip-compressed"
    response["Content-Disposition"] = "attachment; filename=attachments.zip"

    return response
