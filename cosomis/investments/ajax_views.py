from django.db.models import Count,Q
from rest_framework import generics
from rest_framework.response import Response

from administrativelevels.models import AdministrativeLevel
from .models import Sector
from django.http import JsonResponse
from django.views import View
from investments.models import Investment, Sector

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

from django.views import View
from django.http import JsonResponse
from django.db.models import Q, Count
from .models import Investment

class StatisticsView(View):
    def get(self, request, *args, **kwargs):
        # Retrieve filter parameters
        region_id = request.GET.get('region_id')
        prefecture_id = request.GET.get('prefecture_id')
        commune_id = request.GET.get('commune_id')
        canton_id = request.GET.get('canton_id')
        village_id = request.GET.get('village_id')
        project_status = request.GET.get('project-status-filter')

        # Initial queryset
        investments = Investment.objects.all()

        # Apply filters using Q objects
        filters = Q()
        if region_id:
            filters &= Q(administrative_level__parent__parent__parent__parent__id=region_id)
        if prefecture_id:
            filters &= Q(administrative_level__parent__parent__parent__id=prefecture_id)
        if commune_id:
            filters &= Q(administrative_level__parent__parent__id=commune_id)
        if canton_id:
            filters &= Q(administrative_level__parent__id=canton_id)
        if village_id:
            filters &= Q(administrative_level__id=village_id)
        if project_status:
            filters &= Q(project_status=project_status)

        investments = investments.filter(filters)

        # Calculate statistics
        total_communities = investments.values('administrative_level').distinct().count()
        total_subprojects = investments.filter(investment_status=Investment.SUBPROJECT).count()
        subprojects = investments.filter(investment_status=Investment.SUBPROJECT)
        total_completed_infrastructure = investments.filter(project_status=Investment.COMPLETED).count()

        # Sector priorities
        sector_priorities = investments.values('sector__name').annotate(total=Count('sector__name'))

        # Subprojects by sector and minority groups
        minority_groups = [
            'endorsed_by_youth',
            'endorsed_by_women',
            'endorsed_by_agriculturist',
            'endorsed_by_pastoralist'
        ]

        subprojects_by_sector_and_group = {
            group: subprojects.filter(**{group: True}).values('sector__name').annotate(total=Count('sector__name'))
            for group in minority_groups
        }

        # Subprojects with coordinates
        subprojects_with_coordinates = subprojects.exclude(
            administrative_level__latitude__isnull=True,
            administrative_level__longitude__isnull=True
        ).values(
            'id',
            'title',
            'administrative_level__name',
            'administrative_level__latitude',
            'administrative_level__longitude',
            'sector__name',
            'physical_execution_rate'
        )

        data = {
            'total_communities': total_communities,
            'total_subprojects': total_subprojects,
            'total_completed_infrastructure': total_completed_infrastructure,
            'sector_priorities': list(sector_priorities),
            'subprojects_by_sector_and_group': {
                group: list(subprojects_by_sector_and_group[group]) for group in minority_groups
            },
            'subprojects': list(subprojects_with_coordinates)
        }

        return JsonResponse(data)
