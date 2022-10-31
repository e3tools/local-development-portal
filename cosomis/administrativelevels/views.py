from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import DetailView, TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from cosomis.constants import OBSTACLES_FOCUS_GROUP, GOALS_FOCUS_GROUP
from cosomis.mixins import PageMixin
from django.http import Http404
import pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel
from administrativelevels.libraries import convert_file_to_dict
from administrativelevels import functions as administrativelevels_functions
from subprojects.models import VillageObstacle, VillageGoal, VillagePriority, Component


class VillageDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = _('Village')
    active_level1 = 'financial'
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
        


class UploadCSVView(PageMixin, LoginRequiredMixin, TemplateView):
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
        try:
            datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'))
        except pd.errors.ParserError as exc:
            datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'))
        except Exception as exc:
            messages.info(request, _("An error has occurred..."))
        
        message = administrativelevels_functions.save_csv_file_datas_in_db(datas) # call function to save CSV datas in database
        if message:
            messages.info(request, message)

        return redirect('administrativelevels:list')
    
    def get(self, request, *args, **kwargs):
        context = super(UploadCSVView, self).get(request, *args, **kwargs)
        return context


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = AdministrativeLevel.objects.filter(type="Village")
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
        return super().get_queryset()



#Obstacles
class ObstaclesListView(PageMixin, LoginRequiredMixin, ListView):
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
        return ctx

    def get(self, request, *args, **kwargs):
        try:
            ObstaclesListView.administrative_level_id = kwargs['administrative_level_id']
            ObstaclesListView.administrativelevel_village = AdministrativeLevel.objects.get(id=ObstaclesListView.administrative_level_id, type="Village")
            context = super(ObstaclesListView, self).get(request, *args, **kwargs)
            context['obstacles'] = VillageObstacle.objects.filter(administrative_level_id=ObstaclesListView.administrative_level_id)
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
class GoalsListView(PageMixin, LoginRequiredMixin, ListView):
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
        return ctx

    def get(self, request, *args, **kwargs):
        try:
            GoalsListView.administrative_level_id = kwargs['administrative_level_id']
            GoalsListView.administrativelevel_village = AdministrativeLevel.objects.get(id=GoalsListView.administrative_level_id, type="Village")
            context = super(GoalsListView, self).get(request, *args, **kwargs)
            context['goals'] = VillageGoal.objects.filter(administrative_level_id=GoalsListView.administrative_level_id)
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
class PrioritiesListView(PageMixin, LoginRequiredMixin, ListView):
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
        return ctx

    def get(self, request, *args, **kwargs):
        try:
            PrioritiesListView.administrative_level_id = kwargs['administrative_level_id']
            PrioritiesListView.administrativelevel_village = AdministrativeLevel.objects.get(id=PrioritiesListView.administrative_level_id, type="Village")
            context = super(PrioritiesListView, self).get(request, *args, **kwargs)
            context['priorities'] = VillagePriority.objects.filter(administrative_level_id=PrioritiesListView.administrative_level_id)
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



