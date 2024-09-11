import os
import re
import json
import zipfile
import requests
from io import BytesIO
from urllib.parse import urlencode
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.views.generic import DetailView, ListView, CreateView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import BaseFormView
from django.contrib.auth.mixins import LoginRequiredMixin
from usermanager.permissions import AdminPermissionRequiredMixin, IsInvestorMixin
from .forms import AdministrativeLevelForm
from cosomis.mixins import PageMixin
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import QuerySet, Sum, Count, Subquery, Q, Case, When, F, IntegerField
from django.db.models.functions import Coalesce

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Project, Category, Sector
from investments.models import Attachment, Investment, Package

from static.config.datatable import get_datatable_config

from .forms import AttachmentFilterForm, VillageSearchForm, ProjectForm, BulkUploadInvestmentsForm


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
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
        if search:
            if search == "All":
                ads = AdministrativeLevel.objects.filter(type=_type)
                return Paginator(ads, ads.count()).get_page(page_number)
            search = search.upper()
            return Paginator(
                AdministrativeLevel.objects.filter(type=_type, name__icontains=search),
                100,
            ).get_page(page_number)
        else:
            return Paginator(
                AdministrativeLevel.objects.filter(type=_type), 100
            ).get_page(page_number)

        # return super().get_queryset()

    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelsListView, self).get_context_data(**kwargs)
        ctx["search"] = self.request.GET.get("search", None)
        ctx["type"] = self.request.GET.get("type", "Village")
        return ctx


class AdministrativeLevelCreateView(
    PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView
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


class AdministrativeLevelSearchListView(PageMixin, LoginRequiredMixin, ListView):
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
        if search:
            if search == "All":
                ads = AdministrativeLevel.objects.filter(type=_type)
                return Paginator(ads, ads.count()).get_page(page_number)
            search = search.upper()
            return Paginator(
                AdministrativeLevel.objects.filter(type=_type, name__icontains=search),
                100,
            ).get_page(page_number)
        else:
            return Paginator(
                AdministrativeLevel.objects.filter(type=_type), 100
            ).get_page(page_number)

    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelSearchListView, self).get_context_data(**kwargs)
        ctx["form"] = VillageSearchForm()
        ctx["search"] = self.request.GET.get("search", None)
        ctx["type"] = self.request.GET.get("type", "Village")
        ctx["current_language"] = translation.get_language()
        return ctx


class AdministrativeLevelDetailView(
    PageMixin, LoginRequiredMixin, DetailView
):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = "administrative_level/detail/index.html"
    active_level1 = "administrative_levels"

    def post(self, request, *args, **kwargs):
        if 'cart-toggle' in request.POST:
            investment = Investment.objects.get(id=request.POST['cart-toggle'])
            if investment.project_status == Investment.NOT_FUNDED:
                package = Package.objects.get_active_cart(user=self.request.user)
                if package.funded_investments.filter(id=investment.id).exists():
                    package.funded_investments.remove(investment)
                else:
                    package.funded_investments.add(investment)
            return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(AdministrativeLevelDetailView, self).get_context_data(**kwargs)

        if "object" in context:
            context["title"] = "%s %s" % (_(context['object'].type), context['object'].name)
            if context["object"].is_village():
                context["investments"] = Investment.objects.filter(
                    administrative_level=self.object
                )
        admin_level = context.get("object")

        context["context_object_name"] = admin_level.type.lower()

        context['phases'] = self._get_planning_cycle()
        context['development_plan'] = self._get_development_plan(context['phases'])

        tasks_qs = Task.objects.filter(activity__phase__village=admin_level)
        current_task = tasks_qs.filter(status=Task.IN_PROGRESS).first()
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

        images = Attachment.objects.filter(
            Q (adm=admin_level) |
            Q (task__activity__phase__village=admin_level)
        ).exclude(url__icontains='.pdf').all()[:5]
        context["images_data"] = {
            "images": images,
            "exists_at_least_image": len(images) != 0,
            "first_image": images[0] if len(images) > 0 else None,
        }

        context["investments"] = Investment.objects.filter(
            administrative_level=admin_level.id
        )
        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")
        self.object.latitude = 10.693749945416448
        self.object.longitude = 0.330183201548857

        package = Package.objects.get_active_cart(
            user=self.request.user
        )
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


class CommuneDetailView(PageMixin, LoginRequiredMixin, DetailView):

    model = AdministrativeLevel
    template_name = "commune/commune_detail.html"
    active_level1 = "administrative_levels"

    def post(self, request, *args, **kwargs):
        if 'cart-toggle' in request.POST:
            investment = Investment.objects.get(id=request.POST['cart-toggle'])
            if investment.project_status == Investment.NOT_FUNDED:
                package = Package.objects.get_active_cart(user=self.request.user)
                if package.funded_investments.filter(id=investment.id).exists():
                    package.funded_investments.remove(investment)
                else:
                    package.funded_investments.add(investment)
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
        context = super(CommuneDetailView, self).get_context_data(**kwargs)

        if "object" in context:
            context["title"] = "%s %s" % (_(context['object'].type), context['object'].name)
            if context["object"].is_village():
                context["investments"] = Investment.objects.filter(
                    administrative_level=self.object
                )
        admin_level = context.get("object")

        context["context_object_name"] = admin_level.type.lower()

        images = Attachment.objects.filter(
            Q (adm=admin_level) |
            Q (task__activity__phase__village=admin_level)
        ).exclude(url__icontains='.pdf').all()[:5]
        context["images_data"] = {
            "images": images,
            "exists_at_least_image": len(images) != 0,
            "first_image": images[0] if len(images) > 0 else None,
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
        )

        context["investments"] = self._get_queryset(Investment.objects.filter(
            project_status=Investment.NOT_FUNDED,
            administrative_level__in=Subquery(AdministrativeLevel.objects.filter(
                parent__parent=admin_level
            ).values_list('id')
        )))

        context["subprojects"] = Investment.objects.filter(
            administrative_level__in=Subquery(AdministrativeLevel.objects.filter(
                parent__parent=admin_level
            ).values_list('id')
        )).exclude(project_status=Investment.NOT_FUNDED,)
        context["mapbox_access_token"] = os.environ.get("MAPBOX_ACCESS_TOKEN")
        self.object.latitude = 10.693749945416448
        self.object.longitude = 0.330183201548857

        context.update(self._get_priorities_filters())

        return context

    def _get_planning_cycle(self):
        phases = list()
        admin_level = self.object
        for phase in admin_level.phases.all():
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

    def _get_priorities_filters(self):
        context = dict()

        context["categories"] = Category.objects.all()
        if "category-filter" in self.request.GET:
            context["sectors"] = Sector.objects.filter(
                category=self.request.GET["category-filter"]
            )

        context["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {
                "id": "endorsed_by_pastoralist",
                "name": _("Endorsed by ethnic minorities"),
            },
        ]

        context["priorities"] = [
            {"id": 1, "name": _("Priority 1")},
            {"id": 2, "name": _("Priorities 1 and 2")},
            {"id": 3, "name": _("All priorities")}
        ]

        package = Package.objects.get_active_cart(
            user=self.request.user
        )
        context["cart_items_id"] = [inv.id for inv in package.funded_investments.all()]
        return context

    def _get_queryset(self, queryset):

        if "sector-filter" in self.request.GET and self.request.GET[
            "sector-filter"
        ] not in ["", None]:
            queryset = queryset.filter(sector__id=self.request.GET["sector-filter"])
        if "category-filter" in self.request.GET and self.request.GET[
            "category-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                sector__category__id=self.request.GET["category-filter"]
            )

        if "subpopulation-filter" in self.request.GET and self.request.GET[
            "subpopulation-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                **{self.request.GET["subpopulation-filter"]: True}
            )

        if "climate-contribution-filter" in self.request.GET and self.request.GET[
            "climate-contribution-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                climate_contribution=self.request.GET["climate-contribution-filter"]
            )

        if "priorities-filter" in self.request.GET and self.request.GET[
            "priorities-filter"
        ] not in ["", None]:
            priorities = [1]
            if self.request.GET["priorities-filter"] == '2':
                priorities.append(2)
            elif self.request.GET["priorities-filter"] == '3':
                priorities.append(2)
                priorities.append(3)
            queryset = queryset.filter(
                ranking__in=priorities
            )

        return queryset


class ProjectListView(PageMixin, IsInvestorMixin, ListView):
    queryset = Project.objects.all()
    template_name = 'project/list.html'
    context_object_name = "projects"
    title = _("Projects")
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self,*args, object_list=None, **kwargs):
        queryset = object_list if object_list is not None else self.object_list

        context = super().get_context_data(object_list=queryset, **kwargs)

        object_name = self.get_context_object_name(queryset)
        if object_name in context:
            context[object_name] = context[object_name].annotate(investments_count=Count('packages__funded_investments'))
            context[object_name] = context[object_name].annotate(investments_total=Sum('packages__funded_investments__estimated_cost'))
            context['total_mount_invested'] = context[object_name].aggregate(Sum('investments_total'))['investments_total__sum'] or 0

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(owner=self.request.user)
        return queryset


class ProjectDetailView(PageMixin, IsInvestorMixin, BaseFormView, DetailView):
    queryset = Project.objects.all()
    template_name = 'project/detail.html'
    context_object_name = "project"
    form_class = ProjectForm

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if 'investment' in request.POST:
            investment = Investment.objects.filter(
                packages__project=self.object,
            ).get(id=request.POST['investment'])
            investment.project_status = request.POST['status']
            investment.save()
            return super().get(request, *args, **kwargs)

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        self.title = self.object.name
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        project = kwargs["object"]
        context["packages"] = project.packages.all().order_by("created_date")
        inv_ids = list()
        for package in context["packages"]:
            inv_ids += package.funded_investments.all().values_list("id", flat=True)
        context["investments"] = Investment.objects.filter(id__in=inv_ids)
        context["project_status"] = Investment.PROJECT_STATUS_CHOICES
        context["organization"] = project.owner.organization

        if context["organization"] is not None:
            user_qs = context["organization"].users.all().values_list("id")
            investments_qs = Investment.objects.filter(
                packages__user__id__in=Subquery(user_qs)
            )
            context["organization"].total_investments = investments_qs.count()
            context["organization"].total_investments_amount = investments_qs.aggregate(
                Sum("estimated_cost")
            )["estimated_cost__sum"]

        context["datatable_config"] = get_datatable_config()
        context["datatable_config"]["responsive"] = "true"

        context["investments_datatable_config"] = context["datatable_config"].copy()
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
        return context

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = super().get_form_kwargs()
        if hasattr(self, "object"):
            kwargs.update({"instance": self.object})
        return kwargs


class ProjectCreateView(PageMixin, IsInvestorMixin, CreateView):
    template_name = 'project/create/index.html'
    form_class = ProjectForm
    title = _("Create Project")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'owner': self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('administrativelevels:project-upload-investments', kwargs={'pk': self.object.pk})


class BulkUploadInvestmentsView(PageMixin, IsInvestorMixin, SingleObjectMixin, FormView):
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


# Attachments
class AttachmentListView(PageMixin, LoginRequiredMixin, ListView):
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

        context["regions"] = AdministrativeLevel.objects.filter(
            type=AdministrativeLevel.REGION
        )

        query_params: dict = self.request.GET

        context["filter_hierarchy_query_strings"] = self.build_filter_hierarchy()
        context["query_strings_raw"] = query_params.copy()
        context["query_strings_raw"].pop("page", None)
        babylong_query_params_list = [key + '=' + value for key, value in context["query_strings_raw"].items()]
        if babylong_query_params_list:
            context["babylong_query_params"] = '&' + '&'.join(babylong_query_params_list)

        form = AttachmentFilterForm()

        paginator= self.__build_db_filter()

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

        query = query.order_by("created_date")
        paginator = Paginator(query, 36)

        return paginator

    def build_filter_hierarchy(self):
        resp = {}

        def _build_filter_hierarchy(index, get_value):
            current_filter_level = self.filter_hierarchy[index]
            next_filter_level = self.filter_hierarchy[index + 1] if index + 1 < len(self.filter_hierarchy) else None
            if current_filter_level == "task":
                task = Task.objects.get(id=int(get_value))
                resp[current_filter_level] = task.id
                resp[next_filter_level] = task.activity.id
            if current_filter_level == "activity":
                activity = Activity.objects.get(id=int(get_value))
                resp[current_filter_level] = activity.id
                resp[next_filter_level] = activity.phase.id
            if current_filter_level == "phase":
                phase = Phase.objects.get(id=int(get_value))
                resp[current_filter_level] = phase.id
                resp[next_filter_level] = phase.village.id
            if current_filter_level in [adm_type[0].lower() for adm_type in AdministrativeLevel.TYPE]:
                adm_lvl = AdministrativeLevel.objects.get(id=int(get_value))
                resp[current_filter_level] = adm_lvl.id
                if hasattr(adm_lvl, "parent") and adm_lvl.parent is not None and len(self.filter_hierarchy) > index + 1:
                    resp[next_filter_level] = adm_lvl.parent.id

            if len(self.filter_hierarchy) > index + 1:
                return _build_filter_hierarchy(index + 1, resp[next_filter_level])
            return resp

        for idx, key_filter in enumerate(self.filter_hierarchy):
            if key_filter in self.request.GET and self.request.GET[key_filter] not in ['', None]:
                resp = _build_filter_hierarchy(idx, self.request.GET[key_filter])
                return json.dumps(resp)

    def get_queryset(self):
        queryset = super().get_queryset()
        empty_list = ["", None]

        if "tasks" in self.request.GET and self.request.GET["tasks"] not in empty_list:
            queryset = queryset.filter(
                task__id=self.request.GET["tasks"]
            )
        elif "activities" in self.request.GET and self.request.GET["activities"] not in empty_list:
            queryset = queryset.filter(
                task__activity__id=self.request.GET["activities"]
            )
        elif "phase" in self.request.GET and self.request.GET["phase"] not in empty_list:
            queryset = queryset.filter(
                task__activity__phase__id=self.request.GET["phase"]
            )
        else:
            adm_lvls = [adm_name[0].lower() for adm_name in AdministrativeLevel.TYPE]
            adm_list = [adm_type for adm_type in adm_lvls if adm_type in self.request.GET]
            adm_type = adm_list[0] if adm_list else None

            if adm_type and self.request.GET[adm_type] not in empty_list:
                administrative_levels = AdministrativeLevel.objects.get(id=self.request.GET[adm_type])
                descendants = administrative_levels.get_all_descendants()
                queryset = queryset.filter(adm__id__in=[decs.id for decs in descendants])

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
def attachment_download_zip(self, adm_id: int):
    ids = self.GET.get("ids").split(",")

    buffer = BytesIO()
    zip_file = zipfile.ZipFile(buffer, "w")
    for id in ids:
        url = Attachment.objects.get(id=int(id)).url
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
