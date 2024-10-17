import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery
from django.views import generic
from django.http import HttpResponse
from django.http import JsonResponse

from rest_framework import generics, response

from cosomis.mixins import AJAXRequestMixin, JSONResponseMixin
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Sector


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

        d = [{'id': elt.id, 'name': elt.name, 'disabled': self.is_empty(elt)} for elt in data]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)

    def is_empty(self, village):
        phases = village.phases.all().count()
        attachements = village.attachments.all().count()
        return phases == 0 and attachements == 0 and village.total_population ==0
    

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
    template_name = 'administrative_level/detail/task_detail.html'  # Define your template location

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
                    'attachments': [{
                        "name": attachment.name,
                        "type": attachment.type,
                        "order": attachment.order,
                        "attachment": {
                            "uri": attachment.url
                        }
                    } for attachment in task.attachments.all()],  # This is now a properly formatted JSON string or a dict
                },  # This is now a properly formatted JSON string or a dict
            }

            for attachment in task.attachments.all():
                print('----')
                print(attachment.id)
                print(attachment.name)
                print(attachment.type)
                print(attachment.order)
                print(attachment.url)
                print('----')

        else:
            # Optionally handle the case where the task is not found
            context['error'] = 'Task not found'

        return context


class FillAttachmentSelectFilters(generics.GenericAPIView):
    """
    Region -> Prefecture -> Commune -> Canton -> Village
    """

    def post(self, request, *args, **kwargs):
        select_type = request.POST['type']
        child_qs = list()
        if select_type == 'region':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.REGION)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.PREFECTURE)
        elif select_type == 'prefecture':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.PREFECTURE)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.COMMUNE)
        elif select_type == 'commune':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.COMMUNE)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.CANTON)
        elif select_type == 'canton':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.CANTON)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.VILLAGE)
        elif select_type == 'village':
            parent_obj = AdministrativeLevel.objects.get(id=request.POST['value'], type=AdministrativeLevel.VILLAGE)
            child_qs = Phase.objects.filter(village=parent_obj)
        elif select_type == 'phase':
            parent_obj = Phase.objects.get(id=request.POST['value'])
            child_qs = Activity.objects.filter(phase=parent_obj)
        elif select_type == 'activity':
            parent_obj = Activity.objects.get(id=request.POST['value'])
            child_qs = Task.objects.filter(activity=parent_obj)

        return response.Response({
            'values': [{'id': child.id, 'name': child.name} for child in child_qs]
        })


class SectorCodesCSVView(LoginRequiredMixin, generic.View):
    queryset = Sector.objects.all()

    def get(self, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="sectors_codes.csv"'

        writer = csv.writer(response)

        writer.writerow(['id', 'name', 'category'])

        rows = self.queryset.values_list('id', 'name', 'category__name')
        for row in rows:
            writer.writerow(row)

        return response


class VillagesCodesCSVView(LoginRequiredMixin, generic.View):
    queryset = AdministrativeLevel.objects.filter(type=AdministrativeLevel.VILLAGE)

    def get(self, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="administrative_level_codes.csv"'

        writer = csv.writer(response)

        writer.writerow(['id', 'region', 'prefecture', 'commune', 'canton', 'village'])

        rows = self.queryset.values_list('id', 'parent__parent__parent__parent__name', 'parent__parent__parent__name',
                                         'parent__parent__name', 'parent__name', 'name')
        for row in rows:
            writer.writerow(row)

        return response
