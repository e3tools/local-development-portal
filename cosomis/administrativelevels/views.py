from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import DetailView, TemplateView, ListView, CreateView, UpdateView
from django.views.generic.edit import BaseFormView
from django.contrib.auth.mixins import LoginRequiredMixin
from cosomis.constants import OBSTACLES_FOCUS_GROUP, GOALS_FOCUS_GROUP
from cosomis.mixins import PageMixin
from django.http import Http404
import pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q

from no_sql_client import NoSQLClient

from administrativelevels.models import AdministrativeLevel, GeographicalUnit, CVD
from administrativelevels.libraries import convert_file_to_dict, download_file
from administrativelevels import functions as administrativelevels_functions
from subprojects.models import VillageObstacle, VillageGoal, VillagePriority, Component
from .forms import GeographicalUnitForm, CVDForm, AdministrativeLevelForm, FinancialPartnerForm, AttachmentFilterForm
from usermanager.permissions import (
    CDDSpecialistPermissionRequiredMixin, SuperAdminPermissionRequiredMixin,
    AdminPermissionRequiredMixin, AccountantPermissionRequiredMixin
)
from administrativelevels import functions_cvd as cvd_functions
from administrativelevels.functions import (
    get_administrative_level_ids_descendants,
)
from administrativelevels.functions_cvd import save_cvd_instead_of_csv_file_datas_in_db
from financial import function_allocation


class VillageDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = _('Village')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    
    def get_context_data(self, **kwargs):
        context = super(VillageDetailView, self).get_context_data(**kwargs)
        if context.get("object") and context.get("object").type == "Village" : # Verify if the administrativeLevel type is Village
            return context
        raise Http404


class AdministrativeLevelDetailView(PageMixin, LoginRequiredMixin, BaseFormView, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    financial_partner_form_class = FinancialPartnerForm
    nsc_class = NoSQLClient
    no_sql_db_id = None
    no_sql_database_name = "administrative_levels"
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = _('Village')
    active_level1 = 'administrative_levels'
    
    def get_context_data(self, **kwargs):
        context = super(AdministrativeLevelDetailView, self).get_context_data(**kwargs)
        try:
            _type = self.request.GET.get("type", context['object'].type)
        except AttributeError:
            _type = 'village'
        self.template_name = (_type.lower() if _type.lower() in ('village', 'canton') else "administrativelevel") + "_detail.html"
        context['context_object_name'] = _type
        context['title'] = _type
        context['hide_content_header'] = True
        context['administrativelevel_profile'] = context['object']
        village_obj = self._get_village()
        context['priorities'] = self._get_priorities(village_obj)
        context['population'] = self._get_population_data(village_obj)
        context['planning_status'] = self._get_planning_status(village_obj)
        images = self._get_images(village_obj)
        context['adm_id'] = village_obj['adm_id']
        context['images_data'] = {'images': images, "exists_at_least_image": len(images) != 0, 'first_image': images[0]}
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()

        return context

    def get_form_class(self):
        """Return the form class to use."""
        return self.financial_partner_form_class

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        # Next, try looking up by primary key.
        pk = self.kwargs.get(self.pk_url_kwarg)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if pk is not None:
            try:
                pk = int(pk)
                queryset = queryset.filter(pk=pk)
            except ValueError:
                pass

        # Next, try looking up by slug.
        if slug is not None and (pk is None or self.query_pk_and_slug):
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{slug_field: slug})

        # If none of those are defined, it's an error.
        if pk is None and slug is None:
            raise AttributeError(
                "Generic detail view %s must be called with either an object "
                "pk or a slug in the URLconf." % self.__class__.__name__
            )

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
            self.no_sql_db_id = obj.no_sql_db_id
        except (queryset.model.DoesNotExist,  queryset.model.MultipleObjectsReturned):
            self.no_sql_db_id = pk
            obj = self._get_village()
            if obj is None:
                raise Http404(
                    _("No %(verbose_name)s found matching the query")
                    % {"verbose_name": queryset.model._meta.verbose_name}
                )
            obj['pk'] = 0
        return obj

    def _get_nosql_db(self, name=None):
        name = name if name is not None else self.no_sql_database_name
        nsc = self.nsc_class()
        return nsc.get_db(name)

    def _get_village(self):
        nsc = self.nsc_class()
        db = nsc.get_db(self.no_sql_database_name)
        _id = self.no_sql_db_id if self.no_sql_db_id is not None else self.kwargs.get(self.pk_url_kwarg)
        village_document = db.get_query_result(
            {
                "type": "administrative_level",
                "_id": _id
            }
        )[0]
        if len(village_document) > 0:
            return village_document[0]
        return None

    def _get_priorities(self, village):
        try:
            village_obj = village
            if village_obj is not None and 'priorities' in village_obj:
                return village_obj['priorities']
            return []
        except Exception as e:
            return []

    def _get_population_data(self, village):
        try:
            village_obj = village
        except Exception as e:
            return []

        resp = dict()

        if village_obj is not None and 'total_population' in village_obj:
            resp['total_population'] = village_obj['total_population']
        if village_obj is not None and 'population_men' in village_obj:
            resp['population_men'] = village_obj['population_men']
        if village_obj is not None and 'population_women' in village_obj:
            resp['population_women'] = village_obj['population_women']
        if village_obj is not None and 'population_young' in village_obj:
            resp['population_young'] = village_obj['population_young']
        if village_obj is not None and 'population_elder' in village_obj:
            resp['population_elder'] = village_obj['population_elder']
        if village_obj is not None and 'population_handicap' in village_obj:
            resp['population_handicap'] = village_obj['population_handicap']
        if village_obj is not None and 'population_agruculture' in village_obj:
            resp['population_agruculture'] = village_obj['population_agruculture']
        if village_obj is not None and 'population_breeders' in village_obj:
            resp['population_breeders'] = village_obj['population_breeders']
        if village_obj is not None and 'population_minorities' in village_obj:
            resp['population_minorities'] = village_obj['population_minorities']

        return resp

    def _get_planning_status(self, village):
        try:
            village_obj = village
        except Exception as e:
            return []

        resp = dict()

        if village_obj is not None and 'current_phase' in village_obj:
            resp['current_phase'] = village_obj['current_phase']
        if village_obj is not None and 'current_activity' in village_obj:
            resp['current_activity'] = village_obj['current_activity']
        if village_obj is not None and 'current_task' in village_obj:
            resp['current_task'] = village_obj['current_task']
        if village_obj is not None and '% Complete' in village_obj:
            resp['completed'] = village_obj['% Complete'] == 1.0
        if village_obj is not None and 'priorities_identified_date' in village_obj:
            resp['priorities_identified'] = bool(village_obj['priorities_identified_date'])
        else:
            resp['priorities_identified'] = False
        if village_obj is not None and 'village_development_plan_date' in village_obj:
            resp['village_development_plan_date'] = village_obj['village_development_plan_date']
        if village_obj is not None and 'Facilitator' in village_obj:
            resp['facilitator'] = village_obj['Facilitator']['name']
        return resp

    def _get_images(self, village):
        try:
            village_obj = village
            if village_obj is not None and 'attachments' in village_obj:
                return list(filter(lambda x: x.get('type') == 'photo', village_obj['attachments']))
            return []
        except Exception as e:
            return []
        
class AdministrativeLevelCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = AdministrativeLevel
    template_name = 'administrativelevel_create.html'
    context_object_name = 'administrativelevel'
    title = _('Create Administrative level')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
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

    form_class = AdministrativeLevelForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")))
        return context
    
    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")), request.POST)
        if form.is_valid():
            form.save()
            return redirect('administrativelevels:list')
        return super(AdministrativeLevelCreateView, self).get(request, *args, **kwargs)


class AdministrativeLevelUpdateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, UpdateView):
    model = AdministrativeLevel
    template_name = 'administrativelevel_create.html'
    context_object_name = 'administrativelevel'
    title = _('Update Administrative level')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
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

    form_class = AdministrativeLevelForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")), instance=self.get_object())
        return context
    
    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelForm(self.get_parent(self.request.GET.get("type")), request.POST, instance=self.get_object())
        if form.is_valid():
            form.save()
            return redirect('administrativelevels:list')
        return super(AdministrativeLevelUpdateView, self).get(request, *args, **kwargs)
    

class UploadCSVView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, TemplateView):
    """Class to upload and save the administrativelevels"""

    template_name = 'upload.html'
    context_object_name = 'Upload'
    title = _("Upload")
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        datas = {}
        redirect_path = 'administrativelevels:list'
        _type = request.POST.get('_type')
        if _type in ("priority", "subproject"):
            """Upload priorities by csv"""
            redirect_path = "administrativelevels:priorities_priorities"
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_merger_to_dict(
                    request.FILES.get('file'), request.POST.get('sheet_name'),
                    columns_fillna= ["Canton", "Villages", "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"]
                    )
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_merger_to_dict(
                    request.FILES.get('file'), request.POST.get('sheet_name'),
                    columns_fillna= ["Canton", "Villages", "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"]
                    )
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))
            
            try:
                administrative_level_id = request.POST["administrative_level_id"]
                message, file_path = administrativelevels_functions.save_csv_datas_priorities_in_db(datas, administrative_level_id if bool(request.POST.get("administrative_level_id_checkbox")) else 0, _type) # call function to save CSV datas in database
                
                return download_file.download(request, file_path, "text/plain")

                # if message:
                #     messages.info(request, message)
                # return redirect(redirect_path, administrative_level_id=administrative_level_id)
            except Exception as exc:
                raise Http404
        elif _type == "subproject_new":
            """Load Subprojects"""
            redirect_path = "subprojects:list"
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'), request.POST.get('sheet_name'))
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'), request.POST.get('sheet_name'))
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))
            try:
                message, file_path = administrativelevels_functions.save_csv_datas_priorities_in_db(datas, 0, _type) # call function to save CSV datas in database
                
                return download_file.download(request, file_path, "text/plain")
            
            except Exception as exc:
                raise Http404
        
        else:
            datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'))
            try:
                datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'))
            except pd.errors.ParserError as exc:
                datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'))
            except Exception as exc:
                messages.info(request, _("An error has occurred..."))
            
            if _type == "allocation":
                """Load allocation"""
                redirect_path = "financial:financials"
                message, file_path = function_allocation.save_csv_datas_cantons_allocations_in_db(datas)
                return download_file.download(request, file_path, "text/plain")
            elif _type == "cvd":
                """Load CVD"""
                redirect_path = "administrativelevels:cvds_list"
                message = save_cvd_instead_of_csv_file_datas_in_db(datas) # call function to save CSV datas in database
            else:
                """Load Administrative Levels"""
                message = administrativelevels_functions.save_csv_file_datas_in_db(datas) # call function to save CSV datas in database
                
        if message:
            messages.info(request, message)

        return redirect(redirect_path)
    
    def get(self, request, *args, **kwargs):
        context = super(UploadCSVView, self).get(request, *args, **kwargs)
        return context



class DownloadCSVView(PageMixin, LoginRequiredMixin, TemplateView):
    """Class to download administrativelevels under excel file"""

    template_name = 'components/download.html'
    context_object_name = 'Download'
    title = _("Download")
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        file_path = ""
        administrative_level_ids_get = self.request.POST.getlist('value_of_type', None)
        administrative_level_type = self.request.POST.get('type', 'All').title()
        
        administrative_level_type = "All" if administrative_level_type in ("", "null", "undefined") else administrative_level_type
        
        ald_filter_ids = []
        administrative_levels_ids = []
        if not administrative_level_ids_get:
            administrative_level_ids_get.append("")
        for ald_id in administrative_level_ids_get:
            ald_id = 0 if ald_id in ("", "null", "undefined", "All") else ald_id
            administrative_levels_ids += get_administrative_level_ids_descendants(
                ald_id, None, []
            )
            if ald_id:
                ald_filter_ids.append(int(ald_id))
                
        administrative_levels_ids = list(set(administrative_levels_ids))

        try:
            file_path = administrativelevels_functions.get_administratives_levels_under_file_excel_or_csv(
                request.POST.get("file_type"), #file_type=request.POST.get("file_type"),
                administrative_levels_ids
                # params={"type":request.POST.get("type"), "value_of_type":request.POST.get("value_of_type")}
            )

        except Exception as exc:
            messages.info(request, _("An error has occurred..."))

        if not file_path:
            return redirect('administrativelevels:list')
        else:
            return download_file.download(
                request, 
                file_path,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = [] # AdministrativeLevel.objects.filter(type="Village")
    template_name = 'administrativelevels_list.html'
    context_object_name = 'administrativelevels'
    title = _('Administrative levels')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
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
            return Paginator(AdministrativeLevel.objects.filter(type=_type, name__icontains=search), 100).get_page(page_number)
        else:
            return Paginator(AdministrativeLevel.objects.filter(type=_type), 100).get_page(page_number)

        # return super().get_queryset()
    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelsListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        ctx['type'] = self.request.GET.get("type", "Village")
        return ctx
    


#Obstacles
class ObstaclesListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillageObstacle
    template_name = 'priorities/obstacles.html'
    context_object_name = 'obstacles'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'obstacles'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(ObstaclesListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', ObstaclesListView.administrativelevel_village)
        ctx.setdefault('OBSTACLES_FOCUS_GROUP', OBSTACLES_FOCUS_GROUP)

        ctx.setdefault('obstacles', VillageObstacle.objects.filter(administrative_level_id=ObstaclesListView.administrative_level_id).order_by('ranking'))

        return ctx

    def get(self, request, *args, **kwargs):
        try:
            ObstaclesListView.administrative_level_id = kwargs['administrative_level_id']
            ObstaclesListView.administrativelevel_village = AdministrativeLevel.objects.get(id=ObstaclesListView.administrative_level_id, type="Village")
            context = super(ObstaclesListView, self).get(request, *args, **kwargs)
            # context['obstacles'] = VillageObstacle.objects.filter(administrative_level_id=ObstaclesListView.administrative_level_id)
        except Exception as exc:
            raise Http404
        return context
    

    def post(self, request, *args, **kwargs):
        
        group = request.POST.get('group')
        description = request.POST.get('description')
        if group and description:
            '''Add'''
            obstacle = VillageObstacle()
            obstacle.focus_group = group
            obstacle.description = description
            obstacle.administrative_level = ObstaclesListView.administrativelevel_village
            obstacle.meeting_id = 1
            obstacle.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        group = request.POST.get('group-' + id_str)
                        description = request.POST.get('description-' + id_str)
                        if group and description:
                            obstacle = VillageObstacle.objects.get(id=id)
                            obstacle.focus_group = group
                            obstacle.description = description
                            obstacle.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404
        if not description:
            messages.info(request, _("The description is required"))

        return self.get(request, *args, **kwargs)

@login_required
def obstacle_delete(request, obstacle_id):
    """Function to delete one obstacle"""
    administrative_level_id = 0
    try:
        obstacle = VillageObstacle.objects.get(id=obstacle_id)
        administrative_level_id = obstacle.administrative_level_id
        obstacle.delete()
        messages.info(request, _("Obstacle delete successfully"))
    except Exception as exc:
        raise Http404
    
    return redirect('administrativelevels:priorities_obstacles', administrative_level_id=administrative_level_id)



#Goals
class GoalsListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillageGoal
    template_name = 'priorities/goals.html'
    context_object_name = 'goals'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'goals'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(GoalsListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', GoalsListView.administrativelevel_village)
        ctx.setdefault('GOALS_FOCUS_GROUP', GOALS_FOCUS_GROUP)

        ctx.setdefault('goals', VillageGoal.objects.filter(administrative_level_id=GoalsListView.administrative_level_id).order_by('ranking'))

        return ctx

    def get(self, request, *args, **kwargs):
        try:
            GoalsListView.administrative_level_id = kwargs['administrative_level_id']
            GoalsListView.administrativelevel_village = AdministrativeLevel.objects.get(id=GoalsListView.administrative_level_id, type="Village")
            context = super(GoalsListView, self).get(request, *args, **kwargs)
            # context['goals'] = VillageGoal.objects.filter(administrative_level_id=GoalsListView.administrative_level_id)
        except Exception as exc:
            raise Http404
        return context
    

    def post(self, request, *args, **kwargs):
        
        group = request.POST.get('group')
        description = request.POST.get('description')
        if group and description:
            '''Add'''
            goal = VillageGoal()
            goal.focus_group = group
            goal.description = description
            goal.administrative_level = GoalsListView.administrativelevel_village
            goal.meeting_id = 1
            goal.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        group = request.POST.get('group-' + id_str)
                        description = request.POST.get('description-' + id_str)
                        if group and description:
                            goal = VillageGoal.objects.get(id=id)
                            goal.focus_group = group
                            goal.description = description
                            goal.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404
        if not description:
            messages.info(request, _("The description is required"))

        return self.get(request, *args, **kwargs)

@login_required
def goal_delete(request, goal_id):
    """Function to delete one goal"""
    administrative_level_id = 0
    try:
        goal = VillageGoal.objects.get(id=goal_id)
        administrative_level_id = goal.administrative_level_id
        goal.delete()
        messages.info(request, _("Goal delete successfully"))
    except Exception as exc:
        raise Http404
    
    return redirect('administrativelevels:priorities_goals', administrative_level_id=administrative_level_id)



#Priorities
class PrioritiesListView(PageMixin, LoginRequiredMixin, TemplateView):
    model = VillagePriority
    template_name = 'priorities/priorities.html'
    context_object_name = 'priorities'
    title = _('Village development priorities - Cycle 1')
    active_level1 = 'financial'
    active_level2 = 'eligible_priorities'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    administrative_level_id = 0
    administrativelevel_village = None

    def get_context_data(self, **kwargs):
        ctx = super(PrioritiesListView, self).get_context_data(**kwargs)
        ctx.setdefault('administrativelevel_village', PrioritiesListView.administrativelevel_village)
        ctx.setdefault('components', Component.objects.all())
        ctx.setdefault('goals', VillageGoal.objects.filter(administrative_level=PrioritiesListView.administrativelevel_village))
        
        ctx.setdefault('priorities', VillagePriority.objects.filter(administrative_level_id=PrioritiesListView.administrative_level_id).order_by('ranking'))
        
        return ctx

    def get(self, request, *args, **kwargs):
        try:
            PrioritiesListView.administrative_level_id = kwargs['administrative_level_id']
            PrioritiesListView.administrativelevel_village = AdministrativeLevel.objects.get(id=PrioritiesListView.administrative_level_id, type="Village")
            context = super(PrioritiesListView, self).get(request, *args, **kwargs)
            # context['priorities'] = VillagePriority.objects.filter(administrative_level_id=PrioritiesListView.administrative_level_id)
            
        except Exception as exc:
            raise Http404
        return context
    

    def post(self, request, *args, **kwargs):
        
        component_id = request.POST.get('component')
        proposed_men = request.POST.get('proposed_men')
        proposed_women = request.POST.get('proposed_women')
        estimated_cost = request.POST.get('estimated_cost')
        climate_changing_contribution = request.POST.get('climate_changing_contribution')
        if component_id and climate_changing_contribution:
            '''Add'''
            priority = VillagePriority()
            priority.component_id = int(component_id)
            priority.proposed_men = int(proposed_men) if proposed_men else 0
            priority.proposed_women = int(proposed_women) if proposed_women else 0
            priority.estimated_cost = float(estimated_cost) if estimated_cost else 0.0
            priority.climate_changing_contribution = climate_changing_contribution
            priority.administrative_level = PrioritiesListView.administrativelevel_village
            priority.meeting_id = 1
            priority.save()
            messages.info(request, _("Add successfully!"))
        else:
            '''Edit'''
            for key in request.POST:
                if key and type(key) is str and '-' in key and key[-1].isdigit():
                    try:
                        id_str = key.split('-')[-1]
                        id = int(id_str)
                        component_id = int(request.POST.get('component-' + id_str))
                        proposed_men = request.POST.get('proposed_men-' + id_str)
                        proposed_women = request.POST.get('proposed_women-' + id_str)
                        estimated_cost = request.POST.get('estimated_cost-' + id_str)
                        climate_changing_contribution = request.POST.get('climate_changing_contribution-' + id_str)
                        if component_id and climate_changing_contribution:
                            priority = VillagePriority.objects.get(id=id)
                            priority.component_id = component_id
                            priority.proposed_men = int(proposed_men) if proposed_men else 0
                            priority.proposed_women = int(proposed_women) if proposed_women else 0
                            priority.estimated_cost = float(estimated_cost) if estimated_cost else 0.0
                            priority.climate_changing_contribution = climate_changing_contribution
                            priority.save()
                            messages.info(request, _("Update successfully!"))
                            break
                    except Exception as exc:
                        raise Http404
                        
        if not component_id or not climate_changing_contribution:
            messages.info(request, _("Choice one component and give the description!"))

        return self.get(request, *args, **kwargs)


@login_required
def priority_delete(request, priority_id):
    """Function to delete one priority"""
    administrative_level_id = 0
    try:
        priority = VillagePriority.objects.get(id=priority_id)
        administrative_level_id = priority.administrative_level_id
        priority.delete()
        messages.info(request, _("Priority delete successfully"))
    except Exception as exc:
        raise Http404
    
    return redirect('administrativelevels:priorities_priorities', administrative_level_id=administrative_level_id)


# Attachments
class AttachmentListView(PageMixin, LoginRequiredMixin, TemplateView):
    template_name = 'attachments/attachments.html'
    context_object_name = 'attachments'
    title = _("Galerie d'images")
    nsc_class = NoSQLClient
    no_sql_db_id = None
    no_sql_database_name = "village_attachments"

    def get_context_data(self, **kwargs):
        self.activity_choices: List[Tuple] = [(None, '---')]
        self.task_choices: List[Tuple] = [(None, '---')]
        self.phase_choices: List[Tuple] = [(None, '---')]
        context = super(AttachmentListView, self).get_context_data(**kwargs)
        context['attachments'] = []

        try:
            adm_id: int = self.kwargs.get("adm_id")
            query_params: dict = self.request.GET

            form = AttachmentFilterForm()

            nsc: NoSQLClient = self.nsc_class()
            db: Any = nsc.get_db(self.no_sql_database_name)

            village_attachments_document = db.get_query_result(self.__build_db_filter(adm_id, dict()))[0]
            if len(village_attachments_document) > 0:
                self.__get_select_choices(village_attachments_document)

            filtered_village_attachments_document = db.get_query_result(
                self.__build_db_filter(adm_id, query_params))[0]
            if len(filtered_village_attachments_document) > 0:
                context['attachments'] = self.__build_lambda_filter(
                    filtered_village_attachments_document[0].get('attachments', None),
                    query_params
                )

            form.fields.get('type').initial = query_params.get('type')
            form.fields.get('task').choices = self.task_choices
            form.fields.get('task').initial = query_params.get('task')
            form.fields.get('phase').choices = self.phase_choices
            form.fields.get('phase').initial = query_params.get('phase')
            form.fields.get('activity').choices = self.activity_choices
            form.fields.get('activity').initial = query_params.get('activity')
            context['no_results'] = len(context['attachments']) == 0
            context['form'] = form

        except Exception as ex:
            raise Http404
        return context

    def __get_select_choices(self, village_attachments_document) -> None:
        village_attachments = village_attachments_document[0].get('attachments', None)
        self.activity_choices = self.activity_choices + (list(
            set(map(lambda attachment: (attachment.get('activity'), attachment.get('activity')),
                    village_attachments
                    ))))
        self.task_choices = self.task_choices + (list(
            set(map(lambda attachment: (attachment.get('task'), attachment.get('task')),
                    village_attachments
                    ))))
        self.phase_choices = self.phase_choices + (list(
            set(map(lambda attachment: (attachment.get('phase'), attachment.get('phase')),
                    village_attachments
                    ))))

    def __build_lambda_filter(self, attachments: List[any], query_params: dict) -> Optional[List]:
        filters = []

        type_of_document = query_params.get('type')
        if type_of_document is not None and type_of_document is not '':
            filters.append(lambda p: p.get('type') == type_of_document)

        phase = query_params.get('phase')
        if phase is not None and phase is not '':
            filters.append(lambda p: p.get('phase') == phase)

        activity = query_params.get('activity')
        if activity is not None and activity is not '':
            filters.append(lambda p: p.get('activity') == activity)

        task = query_params.get('task')
        if task is not None and task is not '':
            filters.append(lambda p: p.get('task') == task)

        try:
            return list(filter(lambda p: all(f(p) for f in filters), attachments))
        except StopIteration:
            return None

    def __build_db_filter(self, adm_id: int, query_params: dict) -> Dict:
        db_filter: dict = defaultdict(dict)
        db_filter["type"] = self.no_sql_database_name
        db_filter["adm_id"] = adm_id

        if len(query_params) > 0:
            db_filter["attachments"] = defaultdict(dict)
            db_filter["attachments"]["$elemMatch"] = defaultdict(dict)

            type_of_document = query_params.get('type')
            if type_of_document is not None and type_of_document is not '':
                db_filter["attachments"]["$elemMatch"]["type"] = type_of_document

            phase = query_params.get('phase')
            if phase is not None and phase is not '':
                db_filter["attachments"]["$elemMatch"]["phase"] = phase

            activity = query_params.get('activity')
            if activity is not None and activity is not '':
                db_filter["attachments"]["$elemMatch"]["activity"] = activity

            task = query_params.get('task')
            if task is not None and task is not '':
                db_filter["attachments"]["$elemMatch"]["task"] = task

            db_filter["attachments"]["$elemMatch"] = dict(db_filter["attachments"]["$elemMatch"])
            db_filter["attachments"] = dict(db_filter["attachments"])

            if len(db_filter["attachments"]["$elemMatch"]) == 0:
                del (db_filter["attachments"]["$elemMatch"])

            if len(db_filter["attachments"]) == 0:
                del (db_filter["attachments"])

        return dict(db_filter)


#====================== Geographical unit=========================================
class GeographicalUnitListView(PageMixin, LoginRequiredMixin, ListView):
    """Display geographical unit list"""

    model = GeographicalUnit
    queryset = [] #GeographicalUnit.objects.all()
    template_name = 'geographical_unit_list.html'
    context_object_name = 'geographicalunits'
    title = _('Geographical units')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    # def get_queryset(self):
    #     return super().get_queryset()
    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        if search:
            gs = GeographicalUnit.objects.all()
            if search == "All":
                return Paginator(gs, gs.count()).get_page(page_number)
            search = search.upper()
            _gs = []
            for g in gs:
                if search in g.get_name() or (g.canton and search in g.canton.name):
                    _gs.append(g)
            return Paginator(_gs, 100).get_page(page_number)
        else:
            return Paginator(GeographicalUnit.objects.all(), 100).get_page(page_number)
        
    def get_context_data(self, **kwargs):
        ctx = super(GeographicalUnitListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        return ctx

class GeographicalUnitCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = GeographicalUnit
    template_name = 'geographical_unit_create.html'
    context_object_name = 'geographicalunit'
    title = _('Create geographical unit')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
 
    form_class = GeographicalUnitForm # specify the class form to be displayed

    def post(self, request, *args, **kwargs):
        form = GeographicalUnitForm(request.POST)
        if form.is_valid():
            # cvds = form.cleaned_data['cvds']
            villages = form.cleaned_data['villages']
            
            unit = form.save(commit=False)
            # length_str = str(len(GeographicalUnit.objects.all())+1)
            try:
                length_str = str(GeographicalUnit.objects.all().last().pk + 1)
            except Exception as exc:
                length_str = "1"
            # import zlib
            # unit.unique_code = str(zlib.adler32(str(('0'*(9-len(length_str)))+length_str).encode('utf-8')))[:6]
            unit.unique_code = ('0'*(9-len(length_str))) + length_str
            unit = unit.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.geographical_unit = unit
                    village.save()
                except Exception as exc:
                    print(exc)
            
            #Record automatically CVD if unit has one village
            if villages and len(villages) == 1:
                try:
                    length_str_cvd = str(CVD.objects.all().last().pk + 1)
                    cvd = CVD()
                    cvd.name = "Record automatically"
                    cvd.geographical_unit = unit
                    cvd.unique_code = ('0'*(9-len(length_str_cvd))) + length_str_cvd
                    cvd = cvd.save_and_return_object()
                        
                    village = AdministrativeLevel.objects.get(id=int(villages[0]))
                    village.cvd = cvd
                    village.save()

                    cvd.name = village.name
                    cvd.headquarters_village = village
                    cvd.save()
                        

                except Exception as exc:
                    length_str_cvd = "1"
                

                

            return redirect('administrativelevels:geographical_units_list')
        return super(GeographicalUnitCreateView, self).get(request, *args, **kwargs)
    
class GeographicalUnitUpdateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, UpdateView):
    model = GeographicalUnit
    template_name = 'geographical_unit_create.html'
    context_object_name = 'geographicalunit'
    title = _('Update geographical unit')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
 
    form_class = GeographicalUnitForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = GeographicalUnitForm(initial={
            "villages": [
                cat for cat in self.get_object().get_villages().values_list("id", flat=True)
            ]
        }, instance=self.get_object())

        # context['villages'] = self.get_object().geographical_unit.get_villages()

        return context
    def post(self, request, *args, **kwargs):
        form = GeographicalUnitForm(request.POST, instance=self.get_object())
        if form.is_valid():
            # cvds = form.cleaned_data['cvds']
            villages = form.cleaned_data['villages']
            
            unit = form.save(commit=False)
            unit = unit.save_and_return_object()
            unit.administrativelevel_set.clear()
            unit = unit.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.geographical_unit = unit
                    village.save()
                except Exception as exc:
                    print(exc)

            # for cvd_id in cvds:
            #     try:
            #         cvd = CVD.objects.get(id=int(cvd_id))
            #         cvd.geographical_unit = unit
            #         cvd.save()
            #     except Exception as exc:
            #         print(exc)

            return redirect('administrativelevels:geographical_units_list')
        return super(GeographicalUnitUpdateView, self).get(request, *args, **kwargs)

class GeographicalUnitDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one geographical unit"""
    model = GeographicalUnit
    template_name = 'geographical_unit_detail.html'
    context_object_name = 'geographicalunit'
    title = _('Geographical unit')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': reverse_lazy('administrativelevels:geographical_units_list'),
            'title': _('Geographical units')
        },
        {
            'url': '',
            'title': title
        },
    ]
    



#======================================CVD==============================================

class CVDListView(PageMixin, LoginRequiredMixin, ListView):
    """Display geographical unit list"""

    model = CVD
    queryset = [] #CVD.objects.filter()
    template_name = 'cvds_list.html'
    context_object_name = 'cvds'
    title = _('CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    # def get_queryset(self):
    #     return super().get_queryset()
    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        if search:
            if search == "All":
                cs = CVD.objects.all()
                return Paginator(cs, cs.count()).get_page(page_number)
            search = search.upper()
            return Paginator(CVD.objects.filter(
                Q(name__icontains=search) | Q(headquarters_village__parent__name__icontains=search)
            ), 100).get_page(page_number)
        else:
            return Paginator(CVD.objects.all(), 100).get_page(page_number)

    def get_context_data(self, **kwargs):
        ctx = super(CVDListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        return ctx


class CVDCreateView(PageMixin, LoginRequiredMixin, AdminPermissionRequiredMixin, CreateView):
    model = CVD
    template_name = 'cvd_create.html'
    context_object_name = 'cvd'
    title = _('Create CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
 
    form_class = CVDForm # specify the class form to be displayed
    
    def post(self, request, *args, **kwargs):
        form = CVDForm(request.POST)
        if form.is_valid():
            villages = form.cleaned_data['villages']

            cvd = form.save(commit=False)
            # length_str = str(len(CVD.objects.all())+1)
            try:
                length_str = str(CVD.objects.all().last().pk + 1)
            except Exception as exc:
                length_str = "1"
            cvd.unique_code = ('0'*(9-len(length_str))) + length_str
            cvd = cvd.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.cvd = cvd
                    village.save()
                except Exception as exc:
                    print(exc)

            return redirect('administrativelevels:cvds_list')
        return super(CVDCreateView, self).get(request, *args, **kwargs)


class CVDUpdateView(PageMixin, LoginRequiredMixin, AccountantPermissionRequiredMixin, UpdateView):
    model = CVD
    template_name = 'cvd_create.html'
    context_object_name = 'cvd'
    title = _('Update CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
 
    form_class = CVDForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CVDForm(initial={
            "villages": [
                cat for cat in self.get_object().get_villages().values_list("id", flat=True)
            ]
        }, instance=self.get_object())

        # context['villages'] = self.get_object().geographical_unit.get_villages()

        return context
    
    def post(self, request, *args, **kwargs):
        form = CVDForm(request.POST, instance=self.get_object())
        if form.is_valid():
            villages = form.cleaned_data['villages']

            cvd = form.save(commit=False)
            cvd = cvd.save_and_return_object()
            cvd.administrativelevel_set.clear()
            cvd = cvd.save_and_return_object()

            for village_id in villages:
                try:
                    village = AdministrativeLevel.objects.get(id=int(village_id))
                    village.cvd = cvd
                    village.save()
                except Exception as exc:
                    print(exc)

            return redirect('administrativelevels:cvds_list')
        return super(CVDUpdateView, self).get(request, *args, **kwargs)
    
class CVDDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one CVD"""
    model = CVD
    template_name = 'cvd_detail.html'
    context_object_name = 'cvd'
    title = _('CVD')
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': reverse_lazy('administrativelevels:cvds_list'),
            'title': _('CVD')
        },
        {
            'url': '',
            'title': title
        },
    ]

class DownloadCVDCSVView(PageMixin, LoginRequiredMixin, TemplateView):
    """Class to download CVD under excel file"""

    template_name = 'components/download.html'
    context_object_name = 'Download'
    title = _("Download")
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        file_path = ""
        administrative_level_ids_get = self.request.POST.getlist('value_of_type', None)
        administrative_level_type = self.request.POST.get('type', 'All').title()
        
        administrative_level_type = "All" if administrative_level_type in ("", "null", "undefined") else administrative_level_type
        
        ald_filter_ids = []
        administrative_levels_ids = []
        if not administrative_level_ids_get:
            administrative_level_ids_get.append("")
        for ald_id in administrative_level_ids_get:
            ald_id = 0 if ald_id in ("", "null", "undefined", "All") else ald_id
            administrative_levels_ids += get_administrative_level_ids_descendants(
                ald_id, None, []
            )
            if ald_id:
                ald_filter_ids.append(int(ald_id))
                
        administrative_levels_ids = list(set(administrative_levels_ids))

        try:
            file_path = cvd_functions.get_cvd_under_file_excel_or_csv(
                request.POST.get("file_type"), administrative_levels_ids
            )

        except Exception as exc:
            messages.info(request, _("An error has occurred..."))

        if not file_path:
            return redirect('administrativelevels:list')
        else:
            return download_file.download(
                request, 
                file_path,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    