import re
import zipfile
import requests
from io import BytesIO
from urllib.parse import urlencode

from django.conf.urls.static import static
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import translation
from django.views.generic import DetailView, ListView, CreateView
from django.views.generic.edit import BaseFormView
from django.contrib.auth.mixins import LoginRequiredMixin
from usermanager.permissions import AdminPermissionRequiredMixin
from .forms import AdministrativeLevelForm
from cosomis.mixins import PageMixin
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet
from no_sql_client import NoSQLClient

from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task
from investments.models import Attachment, Investment

from .forms import FinancialPartnerForm, AttachmentFilterForm, VillageSearchForm


class VillageDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = "village/village_detail.html"
    context_object_name = "village"
    title = _("Village")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, **kwargs):
        context = super(VillageDetailView, self).get_context_data(**kwargs)

        if "object" in context:
            context["title"] = context["object"].name
            if context["object"].is_village() is True:
                context["investments"] = Investment.objects.filter(
                    administrative_level=self.object
                )
        admin_level = context.get("object")

        tasks_qs = Task.objects.filter(activity__phase__village=admin_level)
        current_task = tasks_qs.filter(status=Task.IN_PROGRESS).first()
        current_phase = current_task.activity.phase
        current_activity = current_task.activity

        task_number = tasks_qs.count()
        tasks_done = tasks_qs.filter(status=Task.COMPLETED).count()
        context["planning_status"] = {
            "current_phase": current_phase,
            "current_activity": current_activity,
            "current_task": current_task,
            "completed": round(float(tasks_done) * 100 / float(task_number), 2),
            "priorities_identified": context["object"].identified_priority,
            "village_development_plan_date": "",
            "facilitator": "",
        }

        if admin_level and admin_level.is_village() is True:
            images = Attachment.objects.filter(
                adm=admin_level.id, type=Attachment.PHOTO
            ).all()
            context["images_data"] = {
                "images": images,
                "exists_at_least_image": len(images) != 0,
                "first_image": images[0] if len(images) > 0 else None,
            }
            investments = Investment.objects.filter(
                administrative_level=admin_level.id
            ).all()
            context["investments"] = investments

            return context
        raise Http404


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = []  # AdministrativeLevel.objects.filter(type="Village")
    template_name = "administrativelevels_list.html"
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
    template_name = "administrativelevel_create.html"
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


class AdministrativeLevelDetailView(
    PageMixin, LoginRequiredMixin, BaseFormView, DetailView
):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    financial_partner_form_class = FinancialPartnerForm
    nsc_class = NoSQLClient
    no_sql_db_id = None
    no_sql_database_name = "purs_test"
    template_name = "village/village_detail.html"
    context_object_name = "village"
    title = _("Village")
    active_level1 = "administrative_levels"

    def get_context_data(self, **kwargs):
        context = super(AdministrativeLevelDetailView, self).get_context_data(**kwargs)
        try:
            _type = self.request.GET.get("type", context["object"].type)
        except AttributeError:
            _type = "village"
        self.template_name = (
            _type.lower()
            if _type.lower() in ("village", "canton")
            else "administrativelevel"
        ) + "_detail.html"
        context["context_object_name"] = _type
        context["title"] = _type
        context["hide_content_header"] = True
        context["administrativelevel_profile"] = context["object"]
        context["priorities"] = Investment.objects.filter(
            administrative_level=self.object
        )
        context["planning_status"] = []
        images = self._get_images(None)
        context["adm_id"] = self.object.id
        context["images_data"] = {
            "images": images,
            "exists_at_least_image": len(images) != 0,
            "first_image": images[0] if len(images) > 0 else None,
        }
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()

        return context

    def get_form_class(self):
        """Return the form class to use."""
        return self.financial_partner_form_class

    def _get_nosql_db(self, name=None):
        name = name if name is not None else self.no_sql_database_name
        nsc = self.nsc_class()
        return nsc.get_db(name)

    def _get_village(self):
        nsc = self.nsc_class()
        db = nsc.get_db(self.no_sql_database_name)
        adm_id = self.kwargs.get(self.pk_url_kwarg)
        village_document = db.get_query_result(
            {"type": "administrative_level", "adm_id": str(adm_id)}
        )
        result = None
        for doc in village_document:
            result = doc
            break
        return result

    def _get_population_data(self, village):
        try:
            village_obj = village
        except Exception as e:
            return []

        resp = dict()

        if village_obj is not None and "total_population" in village_obj:
            resp["total_population"] = village_obj["total_population"]
        if village_obj is not None and "population_men" in village_obj:
            resp["population_men"] = village_obj["population_men"]
        if village_obj is not None and "population_women" in village_obj:
            resp["population_women"] = village_obj["population_women"]
        if village_obj is not None and "population_young" in village_obj:
            resp["population_young"] = village_obj["population_young"]
        if village_obj is not None and "population_elder" in village_obj:
            resp["population_elder"] = village_obj["population_elder"]
        if village_obj is not None and "population_handicap" in village_obj:
            resp["population_handicap"] = village_obj["population_handicap"]
        if village_obj is not None and "population_agruculture" in village_obj:
            resp["population_agruculture"] = village_obj["population_agruculture"]
        if village_obj is not None and "population_breeders" in village_obj:
            resp["population_breeders"] = village_obj["population_breeders"]
        if village_obj is not None and "population_minorities" in village_obj:
            resp["population_minorities"] = village_obj["population_minorities"]
        if village_obj is not None and "languages" in village_obj:
            resp["languages"] = village_obj["languages"]

        return resp

    def _get_planning_status(self, village):
        try:
            village_obj = village
        except Exception as e:
            return []

        resp = dict()

        if village_obj is not None and "current_phase" in village_obj:
            resp["current_phase"] = village_obj["current_phase"]
        if village_obj is not None and "current_activity" in village_obj:
            resp["current_activity"] = village_obj["current_activity"]
        if village_obj is not None and "current_task" in village_obj:
            resp["current_task"] = village_obj["current_task"]
        if village_obj is not None and "% Complete" in village_obj:
            resp["completed"] = village_obj["% Complete"] == 1.0
        if village_obj is not None and "priorities_identified_date" in village_obj:
            resp["priorities_identified"] = bool(
                village_obj["priorities_identified_date"]
            )
        else:
            resp["priorities_identified"] = False
        if village_obj is not None and "village_development_plan_date" in village_obj:
            resp["village_development_plan_date"] = village_obj[
                "village_development_plan_date"
            ]
        if village_obj is not None and "Facilitator" in village_obj:
            resp["facilitator"] = village_obj["Facilitator"]["name"]
        return resp

    def _get_images(self, village):
        try:
            village_obj = village
            if village_obj is not None and "attachments" in village_obj:
                return list(
                    filter(
                        lambda x: x.get("type") == "photo", village_obj["attachments"]
                    )
                )
            return []
        except Exception as e:
            return []


class AdministrativeLevelSearchListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list by parent choice"""

    model = AdministrativeLevel
    queryset = []
    template_name = "administrativelevels_list.html"
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


# Attachments
class AttachmentListView(PageMixin, LoginRequiredMixin, ListView):
    template_name = "attachments/attachments.html"
    context_object_name = "attachments"
    title = _("Gallery")
    model = Attachment

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

        context["administrative_levels"] = AdministrativeLevel.objects.filter(
            type=AdministrativeLevel.VILLAGE
        )

        context["phases"] = Phase.objects.all()
        if "administrative_level" in self.request.GET and self.request.GET[
            "administrative_level"
        ] not in ["", None]:
            context["phases"] = context["phases"].filter(
                village__id=self.request.GET["administrative_level"]
            )

        context["activities"] = Activity.objects.all()
        if "phase" in self.request.GET and self.request.GET["phase"] not in ["", None]:
            context["activities"] = context["activities"].filter(
                phase__id=self.request.GET["phase"]
            )

        context["tasks"] = Task.objects.all()
        if "activities" in self.request.GET and self.request.GET["activities"] not in [
            "",
            None,
        ]:
            context["tasks"] = context["tasks"].filter(
                activity__id=self.request.GET["activities"]
            )

        query_params: dict = self.request.GET

        context["query_strings"] = self.get_query_strings_context()
        context["query_strings_raw"] = query_params.copy()

        form = AttachmentFilterForm()

        paginator: Paginator = self.__build_db_filter()

        context["no_results"] = paginator.count == 0
        context["current_language"] = translation.get_language()
        page_number = query_params.get("page", 1)
        context["attachments"] = paginator.get_page(page_number)
        context["form"] = form
        return context

    def __build_db_filter(self) -> Paginator:
        query: QuerySet = self.get_queryset()

        query = query.order_by("created_date")
        paginator = Paginator(query, 36)

        return paginator

    def get_query_strings_context(self):
        resp = dict()
        for key, value in self.request.GET.items():
            if value not in [None, ""]:
                if key == "administrative_level":
                    resp["Administrative-levels"] = ", ".join(
                        AdministrativeLevel.objects.filter(
                            id__in=[int(value)], type=AdministrativeLevel.VILLAGE
                        ).values_list("name", flat=True)
                    )
                if key == "phase":
                    resp["Phases"] = ", ".join(
                        Phase.objects.filter(id__in=[int(value)]).values_list(
                            "name", flat=True
                        )
                    )
                if key == "activities":
                    resp["Activities"] = ", ".join(
                        Activity.objects.filter(id__in=[int(value)]).values_list(
                            "name", flat=True
                        )
                    )
                if key == "tasks":
                    resp["Tasks"] = ", ".join(
                        Task.objects.filter(id__in=[int(value)]).values_list(
                            "name", flat=True
                        )
                    )
                if key == "types":
                    resp["Types"] = [value]

        return resp

    def get_queryset(self):
        queryset = super().get_queryset()
        if "administrative_level" in self.request.GET and self.request.GET[
            "administrative_level"
        ] not in ["", None]:
            if "phase" in self.request.GET and self.request.GET["phase"] not in [
                "",
                None,
            ]:
                queryset = queryset.filter(
                    Q(adm__id=self.request.GET["administrative_level"])
                    | Q(task__activity__phase__id=self.request.GET["phase"])
                )
            elif "activities" in self.request.GET and self.request.GET[
                "activities"
            ] not in ["", None]:
                queryset = queryset.filter(
                    Q(adm__id=self.request.GET["administrative_level"])
                    | Q(task__activity__id=self.request.GET["activities"])
                )
            elif "tasks" in self.request.GET and self.request.GET["tasks"] not in [
                "",
                None,
            ]:
                queryset = queryset.filter(
                    Q(adm__id=self.request.GET["administrative_level"])
                    | Q(task__id=self.request.GET["tasks"])
                )
            else:
                queryset = queryset.filter(
                    adm__id=self.request.GET["administrative_level"]
                )
        else:
            if "phase" in self.request.GET and self.request.GET["phase"] not in [
                "",
                None,
            ]:
                queryset = queryset.filter(
                    adm__id=self.request.GET["administrative_level"]
                )
            elif "activities" in self.request.GET and self.request.GET[
                "activities"
            ] not in ["", None]:
                queryset = queryset.filter(
                    adm__id=self.request.GET["administrative_level"]
                )
            elif "tasks" in self.request.GET and self.request.GET["tasks"] not in [
                "",
                None,
            ]:
                queryset = queryset.filter(
                    adm__id=self.request.GET["administrative_level"]
                )

        return queryset


class VillageAttachmentListView(AttachmentListView):
    def get_context_data(self, **kwargs):
        context = super(VillageAttachmentListView, self).get_context_data(**kwargs)
        if context["administrative_level"].is_village() is False:
            raise Http404

        return context


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


# Commune
class CommuneDetailView(PageMixin, LoginRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "commune/commune_detail.html"
    context_object_name = "commune"
    title = _("Commune")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, **kwargs):
        context = super(CommuneDetailView, self).get_context_data(**kwargs)
        admin_level = context.get("object")
        if admin_level and admin_level.is_commune() is True:
            images = Attachment.objects.filter(
                adm=admin_level.id, type=Attachment.PHOTO
            ).all()
            context["images_data"] = {
                "images": images,
                "exists_at_least_image": len(images) != 0,
                "first_image": images[0] if len(images) > 0 else None,
            }
            investments = Investment.objects.filter(
                administrative_level=admin_level.id
            ).all()
            context["investments"] = investments
            return context
        raise Http404


class CommuneAttachmentListView(AttachmentListView):
    def get_context_data(self, **kwargs):
        context = super(CommuneAttachmentListView, self).get_context_data(**kwargs)

        if context["administrative_level"].is_commune() is False:
            raise Http404

        return context


# Canton
class CantonDetailView(PageMixin, LoginRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "canton/canton_detail.html"
    context_object_name = "canton"
    title = _("Canton")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, **kwargs):
        context = super(CantonDetailView, self).get_context_data(**kwargs)
        admin_level = context.get("object")
        if admin_level and admin_level.is_canton() is True:
            images = Attachment.objects.filter(
                adm=admin_level.id, type=Attachment.PHOTO
            ).all()
            context["images_data"] = {
                "images": images,
                "exists_at_least_image": len(images) != 0,
                "first_image": images[0] if len(images) > 0 else None,
            }
            investments = Investment.objects.filter(
                administrative_level=admin_level.id
            ).all()
            context["investments"] = investments
            return context
        raise Http404


class CantonAttachmentListView(AttachmentListView):
    def get_context_data(self, **kwargs):
        context = super(CantonAttachmentListView, self).get_context_data(**kwargs)

        if context["administrative_level"].is_canton() is False:
            raise Http404

        return context


# Region
class RegionDetailView(PageMixin, LoginRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "region/region_detail.html"
    context_object_name = "region"
    title = _("Region")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, **kwargs):
        context = super(RegionDetailView, self).get_context_data(**kwargs)
        admin_level = context.get("object")
        if admin_level and admin_level.is_region() is True:
            images = Attachment.objects.filter(
                adm=admin_level.id, type=Attachment.PHOTO
            ).all()
            context["images_data"] = {
                "images": images,
                "exists_at_least_image": len(images) != 0,
                "first_image": images[0] if len(images) > 0 else None,
            }
            investments = Investment.objects.filter(
                administrative_level=admin_level.id
            ).all()
            context["investments"] = investments
            return context
        raise Http404


# Prefecture
class PrefectureDetailView(PageMixin, LoginRequiredMixin, DetailView):
    model = AdministrativeLevel
    template_name = "prefecture/prefecture_detail.html"
    context_object_name = "prefecture"
    title = _("Prefecture")
    active_level1 = "administrative_levels"
    breadcrumb = [
        {"url": "", "title": title},
    ]

    def get_context_data(self, **kwargs):
        context = super(PrefectureDetailView, self).get_context_data(**kwargs)
        admin_level = context.get("object")
        if admin_level and admin_level.is_prefecture() is True:
            images = Attachment.objects.filter(
                adm=admin_level.id, type=Attachment.PHOTO
            ).all()
            context["images_data"] = {
                "images": images,
                "exists_at_least_image": len(images) != 0,
                "first_image": images[0] if len(images) > 0 else None,
            }
            investments = Investment.objects.filter(
                administrative_level=admin_level.id
            ).all()
            context["investments"] = investments
            return context
        raise Http404
