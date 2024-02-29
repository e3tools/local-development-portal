from rest_framework import generics
from rest_framework.response import Response

from administrativelevels.models import AdministrativeLevel
from .models import Sector


class FillAdmLevelsSelectFilters(generics.GenericAPIView):
    """
    Region -> Prefecture -> Commune -> Canton -> Village
    """

    def post(self, request, *args, **kwargs):
        adm_obj = AdministrativeLevel.objects.get(id=request.POST['value'])
        opt_qs = AdministrativeLevel.objects.filter(parent=adm_obj)
        if adm_obj.type == AdministrativeLevel.REGION:
            opt_qs = opt_qs.filter(type=AdministrativeLevel.PREFECTURE)
        elif adm_obj.type == AdministrativeLevel.PREFECTURE:
            opt_qs = opt_qs.filter(type=AdministrativeLevel.COMMUNE)
        elif adm_obj.type == AdministrativeLevel.COMMUNE:
            opt_qs = opt_qs.filter(type=AdministrativeLevel.CANTON)
        elif adm_obj.type == AdministrativeLevel.CANTON:
            opt_qs = opt_qs.filter(type=AdministrativeLevel.VILLAGE)

        return Response({
            'values': [{'id': adm.id, 'name': adm.name} for adm in opt_qs]
        })


class FillSectorsSelectFilters(generics.GenericAPIView):
    """
    Region -> Prefecture -> Commune -> Canton -> Village
    """

    def post(self, request, *args, **kwargs):
        opt_qs = Sector.objects.filter(category__id=request.POST['value'])
        return Response({
            'values': [{'id': adm.id, 'name': adm.name} for adm in opt_qs]
        })
