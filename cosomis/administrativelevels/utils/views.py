import json
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import generic

from cosomis.mixins import AJAXRequestMixin, JSONResponseMixin
from administrativelevels.models import AdministrativeLevel

from investments.models import Task


class GetAdministrativeLevelForCVDByADLView(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        adl_id = request.GET.get('administrative_level_id')

        objects = AdministrativeLevel.objects.filter(id=int(adl_id))
        d = []
        if objects:
            obj = objects.first()
            if obj.cvd:
                d = [{'id': elt.id, 'name': elt.name} for elt in obj.cvd.get_villages()]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)

class GetChoicesForNextAdministrativeLevelNoConditionView(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')

        data = AdministrativeLevel.objects.filter(parent_id=int(parent_id))

        d = [{'id': elt.id, 'name': elt.name} for elt in data]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)
    

class GetChoicesForNextAdministrativeLevelView(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')
        geographical_unit_id = request.GET.get('geographical_unit_id', None)

        data = AdministrativeLevel.objects.filter(parent_id=int(parent_id))

        d = [{'id': elt.id, 'name': elt.name} for elt in data if((not elt.geographical_unit) or (elt.geographical_unit and geographical_unit_id and elt.geographical_unit.id == int(geographical_unit_id)))]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)

class GetChoicesAdministrativeLevelByGeographicalUnitView(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        geographical_unit_id = request.GET.get('geographical_unit_id')
        cvd_id = request.GET.get('cvd_id', None)

        data = AdministrativeLevel.objects.filter(geographical_unit=int(geographical_unit_id))

        d = [{'id': elt.id, 'name': elt.name} for elt in data if((not elt.cvd) or (elt.cvd and cvd_id and elt.cvd.id == int(cvd_id)))]
        
        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)
    

class GetAncestorAdministrativeLevelsView(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        administrative_id = request.GET.get('administrative_id', None)
        ancestors = []
        try:
            ancestors.insert(0, str(AdministrativeLevel.objects.get(id=int(administrative_id)).parent.id))
        except Exception as exc:
            pass

        return self.render_to_json_response(ancestors, safe=False)


class TaskDetailAjaxView(generic.TemplateView):
    template_name = 'village/task_detail.html'  # Define your template location

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Get task id from URL parameters
        task_id = self.kwargs.get('pk', None)
        task = Task.objects.filter(id=task_id).first()

        if task:
            # Ensure dict_form_responses is a valid JSON string or dict
            # Adding task details to the context
            context['task'] = {
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'task': {
                    'form_response': task.form_responses,  # This is now a properly formatted JSON string or a dict
                    'form': task.form,  # This is now a properly formatted JSON string or a dict
                },  # This is now a properly formatted JSON string or a dict
            }
        else:
            # Optionally handle the case where the task is not found
            context['error'] = 'Task not found'

        return context
