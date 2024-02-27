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


class TaskDetailAjaxView(generic.View):

    def get(self, request, *args, **kwargs):

        task = Task.objects.filter(id=kwargs.get('pk', None)).first()

        if task is not None:
            # Ensure dict_form_responses is a valid JSON string
            try:
                # Attempt to load it as JSON to check if it's already valid JSON
                dict_form_responses = json.loads(task.dict_form_responses)
            except TypeError:
                # If it's a Python dict, serialize it. If it's already a string, this step is not needed.
                dict_form_responses = task.dict_form_responses
            except json.JSONDecodeError:
                # If the string is not valid JSON, this handles the case and serializes a Python dict
                dict_form_responses = json.dumps(task.dict_form_responses)

            response = {
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'meta': dict_form_responses  # This should now be a properly formatted JSON string
            }

            return JsonResponse(response)