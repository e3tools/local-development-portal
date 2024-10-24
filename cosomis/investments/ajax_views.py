import math

from django.db.models import Count, Q, Subquery, F, Sum
from django.http import JsonResponse
from django.views import View

from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from administrativelevels.models import AdministrativeLevel, Sector
from .models import Investment, Package
from .serializers import InvestmentSerializer


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


class InvestmentModelViewSet(ModelViewSet):
    queryset = Investment.objects.filter(
        investment_status=Investment.PRIORITY,
        project_status=Investment.NOT_FUNDED
    )
    serializer_class = InvestmentSerializer

    @action(detail=False, methods=['POST'], url_path='results', url_name='results')
    def selected_investments_data(self, request, *args, **kwargs):
        qs = self.get_queryset()
        inv_ids = request.data['selected_ids'].split('-')
        if '' in inv_ids: inv_ids.remove('')

        qs = qs.exclude(id__in=inv_ids) if request.data['all_queryset'] == 'true' else qs.filter(id__in=inv_ids)

        return Response({
            'total_funding_display': qs.aggregate(total_funding_display=Sum('estimated_cost'))['total_funding_display'] or 0,
            'total_villages_display': qs.values('administrative_level').distinct().count(),
            'total_subprojects_display': qs.count()
        })

    def get_serializer_context(self):
        context = {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self
        }
        if 'all_queryset' in self.request.query_params:
            context['all_queryset'] = self.request.query_params['all_queryset']
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if "region-filter" in self.request.GET and self.request.GET[
            "region-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__parent__id=self.request.GET[
                    "region-filter"
                ],
                administrative_level__parent__parent__parent__parent__type=AdministrativeLevel.REGION,
            )
        if "prefecture-filter" in self.request.GET and self.request.GET[
            "prefecture-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__id=self.request.GET[
                    "prefecture-filter"
                ],
                administrative_level__parent__parent__parent__type=AdministrativeLevel.PREFECTURE,
            )
        if "commune-filter" in self.request.GET and self.request.GET[
            "commune-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__id=self.request.GET[
                    "commune-filter"
                ],
                administrative_level__parent__parent__type=AdministrativeLevel.COMMUNE,
            )
        if "canton-filter" in self.request.GET and self.request.GET[
            "canton-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__id=self.request.GET["canton-filter"],
                administrative_level__parent__type=AdministrativeLevel.CANTON,
            )
        if "village-filter" in self.request.GET and self.request.GET[
            "village-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__id=self.request.GET["village-filter"],
                administrative_level__type=AdministrativeLevel.VILLAGE,
            )

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

        if "is-funded-filter" in self.request.GET and self.request.GET[
            "is-funded-filter"
        ] not in ["", None]:
            if self.request.GET["is-funded-filter"] == 'true':
                queryset = queryset.exclude(project_status=Investment.NOT_FUNDED)
            else:
                queryset = queryset.exclude(
                    project_status=Investment.FUNDED
                )

        return queryset


class StatisticsView(View):
    def get(self, request, *args, **kwargs):
        # Retrieve filter parameters
        region_id = request.GET.get('region_id', None)
        prefecture_id = request.GET.get('prefecture_id', None)
        commune_id = request.GET.get('commune_id', None)
        canton_id = request.GET.get('canton_id', None)
        village_id = request.GET.get('village_id', None)
        project_status = request.GET.get('project-status-filter', None)
        organization = request.GET.get('organization', None)
        sector = request.GET.get('sector', None)
        sector_type = request.GET.get('type', None)
        sector_type_list = []
        sector_filter_active = False
        # Initial queryset
        investments = Investment.objects.all()
        # Apply filters using Q objects
        filters = Q()
        if village_id and village_id is not None:
            filters &= Q(administrative_level__id=village_id)
        elif canton_id and canton_id is not None:
            filters &= Q(administrative_level__parent__id=canton_id)
        elif commune_id and commune_id is not None:
            filters &= Q(administrative_level__parent__parent__id=commune_id)
        elif prefecture_id and prefecture_id is not None:
            filters &= Q(administrative_level__parent__parent__parent__id=prefecture_id)
        elif region_id and region_id is not None:
            filters &= Q(administrative_level__parent__parent__parent__parent__id=region_id)

        if project_status and project_status is not None:
            filters &= Q(project_status=project_status)
        if organization and organization is not None:
            filters &= Q(packages__in=(Subquery(Package.objects.filter(project__owner__organization=organization).values('funded_investments'))))
        if sector and sector is not None:
            sector_type_list = list(Sector.objects.filter(category=sector).values('id', 'name'))
            sector_filter_active = True
            filters &= Q(sector__category=sector)
        if sector_type and sector_type is not None:
            filters &= Q(sector=sector_type)

        investments = investments.filter(filters)

        # Calculate statistics
        total_communities = investments.values('administrative_level').distinct().count()
        total_investments = investments.count()
        total_subprojects = investments.exclude(funded_by=None).count()
        subprojects = investments.filter(investment_status=Investment.SUBPROJECT)
        total_completed_infrastructure = investments.filter(project_status=Investment.COMPLETED).count()
        total_funded_priorities = investments.filter(investment_status=Investment.PRIORITY, funded_by__isnull=False).count()
        total_unfunded_priorities = investments.filter(investment_status=Investment.PRIORITY,funded_by__isnull=True).count()
        # Subprojects by sector and minority groups
        minority_groups = [
            'endorsed_by_youth',
            'endorsed_by_women',
            'endorsed_by_agriculturist',
            'endorsed_by_pastoralist'
        ]

        # Sector priorities
        if sector_filter_active:
            sector_priorities = investments.values('sector__name').annotate(
                sector__category__name=F('sector__name'),  # Rename the key here
                total=Count('sector__name')
            )
            subprojects_by_sector_and_group = {
                group: investments.filter(**{group: True}).values('sector__name').annotate(
                    sector__category__name=F('sector__name'),  # Rename the key here
                    total=Count('sector__name')
                )
                for group in minority_groups
            }
        else:
            sector_priorities = investments.values('sector__category__name').annotate(
                total=Count('sector__category__name'))
            subprojects_by_sector_and_group = {
                group: investments.filter(**{group: True}).values('sector__category__name').annotate(
                    total=Count('sector__category__name'))
                for group in minority_groups
            }


        # Fetch subprojects that have non-null latitude and longitude
        subprojects_with_coordinates = investments.exclude(
            latitude__isnull=True,
            longitude__isnull=True
        ).values(
            'id',
            'title',
            'administrative_level__name',
            'latitude',
            'longitude',
            'sector__name',
            'physical_execution_rate'
        )

        # Filter out subprojects with NaN latitude or longitude
        filtered_subprojects = [
            subproject for subproject in subprojects_with_coordinates
            if not (math.isnan(subproject['latitude']) or math.isnan(subproject['longitude']))
        ]

        data = {
            'total_communities': total_communities,
            'total_investments': total_investments,
            'total_subprojects': total_subprojects,
            'total_completed_infrastructure': total_completed_infrastructure,
            'sector_priorities': list(sector_priorities),
            'sector_types': sector_type_list,
            'subprojects_by_sector_and_group': {
                group: list(subprojects_by_sector_and_group[group]) for group in minority_groups
            },
            'subprojects': filtered_subprojects,  # Use the filtered subprojects without NaN
            'total_funded_priorities': total_funded_priorities,
            'total_unfunded_priorities': total_unfunded_priorities,
        }

        return JsonResponse(data)
