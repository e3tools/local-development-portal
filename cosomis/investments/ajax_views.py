import math
from xml.sax.handler import property_interning_dict

from django.db.models import Count, Q, Subquery, F, Sum, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.views import View

from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response

from administrativelevels.models import AdministrativeLevel, Sector, Project, GeoSegment
from .models import Investment, Package, PackageFundedInvestment, Attachment
from .serializers import InvestmentSerializer, PriorityInvestmentSerializer
from cosomis.constants import IMAGE_EXTENSIONS
from utils.mixpanel.utils import track_user_activity


def apply_climate_filters(queryset, get_params):
    apply_filter = False
    geoseg_queryset = GeoSegment.objects.all()
    if "temperature-max-filter" in get_params and get_params[
        "temperature-max-filter"] not in ["", None]:
        geoseg_queryset = geoseg_queryset.filter(tmmx_avg_2020_diff__lte=get_params["temperature-max-filter"])
        apply_filter = True
    if "temperature-min-filter" in get_params and get_params[
        "temperature-min-filter"] not in ["", None]:
        geoseg_queryset = geoseg_queryset.filter(tmmx_avg_2020_diff__gte=get_params["temperature-min-filter"])
        apply_filter = True

    if "precipitation-min-filter" in get_params and get_params[
        "precipitation-min-filter"] not in ["", None]:
        geoseg_queryset = geoseg_queryset.filter(pr_avg_2020_diff__lte=get_params["precipitation-min-filter"])
        apply_filter = True
    if "precipitation-max-filter" in get_params and get_params[
        "precipitation-max-filter"] not in ["", None]:
        geoseg_queryset = geoseg_queryset.filter(pr_avg_2020_diff__gte=get_params["precipitation-max-filter"])
        apply_filter = True

    if "land-type-filter" in get_params and get_params[
        "land-type-filter"] not in ["", None]:
        geoseg_queryset = geoseg_queryset.filter(lc_gencat_20=get_params["land-type-filter"])
        apply_filter = True

    if apply_filter:
        return queryset.filter(administrative_level__geo_segment__id__in=Subquery(geoseg_queryset.values("id")))
    else:
        return queryset


class FillAdmLevelsSelectFilters(generics.GenericAPIView):
    """
    Region -> Prefecture -> Commune -> Canton -> Village
    """

    def post(self, request, *args, **kwargs):
        adm_obj = AdministrativeLevel.objects.get(id=request.POST['value'])
        opt_qs = AdministrativeLevel.objects.filter(parent=adm_obj)
        if adm_obj.is_region():
            opt_qs = opt_qs.filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.PREFECTURE)
            )
        elif adm_obj.is_prefecture():
            opt_qs = opt_qs.filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.COMMUNE)
            )
        elif adm_obj.is_commune():
            opt_qs = opt_qs.filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.CANTON)
            )
        elif adm_obj.is_canton():
            opt_qs = opt_qs.filter(
                AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
            )

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


def get_selectable_investments_base_queryset():
    """Investissements prioritaires non encore financés, hors paquets actifs (en attente ou approuvés).
    Les investissements rejetés (tous leurs items dans un paquet sont REJECTED) sont réintégrés
    afin qu'un autre partenaire puisse les sélectionner."""
    rejected_investment_ids = PackageFundedInvestment.objects.filter(
        status=PackageFundedInvestment.REJECTED
    ).values_list("investment_id", flat=True)

    active_investment_ids = PackageFundedInvestment.objects.filter(
        status__in=[PackageFundedInvestment.PENDING_APPROVAL, PackageFundedInvestment.APPROVED]
    ).values_list("investment_id", flat=True)

    return Investment.objects.filter(
        investment_status=Investment.PRIORITY,
    ).filter(
        # funded_by nul (jamais soumis) OU tous les items du paquet ont été rejetés
        Q(funded_by__isnull=True) | Q(id__in=rejected_investment_ids)
    ).exclude(
        # Exclure les items actuellement en attente ou approuvés dans un paquet actif
        id__in=active_investment_ids
    )


def get_selectable_investments_queryset(get_params):
    """Applique à `get_selectable_investments_base_queryset()` tous les filtres GET
    utilisés par la page /investments/ (region/prefecture/.../is-funded-filter).

    Cette fonction est LA source unique de vérité pour "quels investissements
    l'utilisateur voit et peut sélectionner" : elle est utilisée à la fois par
    le datatable (InvestmentModelViewSet.get_queryset) et par la soumission du
    panier en mode "tout sélectionner" (InvestmentsForm.clean). Les deux doivent
    rester synchronisés, sans quoi "Ajouter au panier" en mode select-all peut
    ajouter des investissements qui ne correspondent pas aux filtres affichés.
    """
    queryset = get_selectable_investments_base_queryset()

    if "region-filter" in get_params and get_params["region-filter"] not in ["", None]:
        queryset = queryset.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.REGION,
                field="administrative_level__parent__parent__parent__parent__type",
            ),
            administrative_level__parent__parent__parent__parent__id=get_params["region-filter"],
        )
    if "prefecture-filter" in get_params and get_params["prefecture-filter"] not in ["", None]:
        queryset = queryset.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.PREFECTURE,
                field="administrative_level__parent__parent__parent__type",
            ),
            administrative_level__parent__parent__parent__id=get_params["prefecture-filter"],
        )
    if "commune-filter" in get_params and get_params["commune-filter"] not in ["", None]:
        queryset = queryset.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.COMMUNE,
                field="administrative_level__parent__parent__type",
            ),
            administrative_level__parent__parent__id=get_params["commune-filter"],
        )
    if "canton-filter" in get_params and get_params["canton-filter"] not in ["", None]:
        queryset = queryset.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.CANTON,
                field="administrative_level__parent__type",
            ),
            administrative_level__parent__id=get_params["canton-filter"],
        )
    if "village-filter" in get_params and get_params["village-filter"] not in ["", None]:
        queryset = queryset.filter(
            AdministrativeLevel.type_filter_q(
                AdministrativeLevel.VILLAGE,
                field="administrative_level__type",
            ),
            administrative_level__id=get_params["village-filter"],
        )

    if "sector-filter" in get_params and get_params["sector-filter"] not in ["", None]:
        queryset = queryset.filter(sector__id=get_params["sector-filter"])
    if "category-filter" in get_params and get_params["category-filter"] not in ["", None]:
        queryset = queryset.filter(sector__category__id=get_params["category-filter"])

    if "subpopulation-filter" in get_params and get_params["subpopulation-filter"] not in ["", None]:
        queryset = queryset.filter(**{get_params["subpopulation-filter"]: True})

    if "climate-contribution-filter" in get_params and get_params["climate-contribution-filter"] not in ["", None]:
        queryset = queryset.filter(climate_contribution=get_params["climate-contribution-filter"])

    if "priorities-filter" in get_params and get_params["priorities-filter"] not in ["", None]:
        priorities = [1]
        if get_params["priorities-filter"] == '2':
            priorities.append(2)
        elif get_params["priorities-filter"] == '3':
            priorities.append(2)
            priorities.append(3)
        queryset = queryset.filter(ranking__in=priorities)

    if "is-funded-filter" in get_params and get_params["is-funded-filter"] not in ["", None]:
        if get_params["is-funded-filter"] == 'true':
            queryset = queryset.exclude(project_status=Investment.NOT_FUNDED)
        else:
            queryset = queryset.exclude(project_status=Investment.FUNDED)

    queryset = apply_climate_filters(queryset, get_params)

    return queryset


class InvestmentModelViewSet(ModelViewSet):
    queryset = Investment.objects.none()  # Requis par DRF ; surchargé par get_queryset()
    serializer_class = InvestmentSerializer

    def get_base_queryset(self):
        return get_selectable_investments_base_queryset()

    @action(detail=False, methods=['POST'], url_path='results', url_name='results')
    def selected_investments_data(self, request, *args, **kwargs):
        qs = self.get_queryset()
        inv_ids = request.data['selected_ids'].split('-')
        if '' in inv_ids: inv_ids.remove('')
        try:
            if request.data['project_id']:
                project = Project.objects.filter(id=request.data['project_id']).first()
                project_amount = project.total_amount
                project_id = project.id
            else:
                project_amount = 0
                project_id = None
        except:
            project_amount = 0
            project_id = None

        qs = qs.exclude(id__in=inv_ids) if request.data['all_queryset'] == 'true' else qs.filter(id__in=inv_ids)

        return Response({
            'total_funding_display': qs.aggregate(total_funding_display=Sum('estimated_cost'))['total_funding_display'] or 0,
            'total_villages_display': qs.values('administrative_level').distinct().count(),
            'total_subprojects_display': qs.count(),
            'project_total_fund': project_amount,
            'project_id': project_id,
        })

    @action(detail=False, methods=['POST'], url_path='total-results', url_name='total_results')
    def total_investments_data(self, request, *args, **kwargs):
        qs = self.get_queryset()
        try:
            if request.data['project_id']:
                project = Project.objects.filter(id=request.data['project_id']).first()
                project_amount = project.total_amount
                project_id = project.id
            else:
                project_amount = 0
                project_id = None
        except:
            project_amount = 0
            project_id = None

        return Response({
            'total_funding_display': qs.aggregate(total_funding_display=Sum('estimated_cost'))['total_funding_display'] or 0,
            'total_villages_display': qs.values('administrative_level').distinct().count(),
            'total_subprojects_display': qs.count(),
            'project_total_fund': project_amount,
            'project_id': project_id,
        })

    def get_serializer_context(self):
        try:
            project = Project.objects.filter(id=self.request.query_params['project_id']).first() if 'project_id' in self.request.query_params and self.request.query_params['project_id'] else None
        except:
            project = None
        context = {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'project_total_fund': project.total_amount if project is not None else 0,
            'project_id': project.id if project is not None else None,
        }
        if 'all_queryset' in self.request.query_params:
            context['all_queryset'] = self.request.query_params['all_queryset']
        return context

    def get_queryset(self):
        return get_selectable_investments_queryset(self.request.GET)


class SubtreeInvestmentsViewSet(ReadOnlyModelViewSet):
    """Investissements de tout le sous-arbre d'un niveau administratif (région,
    préfecture, ...) jusqu'aux villages : alimente l'onglet "Priorités" avec
    une pagination server-side (DataTables), comme /investments/, au lieu du
    tableau HTML unique et non paginé que rendait `shared/priorities_table.html`.
    """
    queryset = Investment.objects.none()  # Requis par DRF ; surchargé par get_queryset()
    serializer_class = PriorityInvestmentSerializer

    def get_queryset(self):
        admin_level = AdministrativeLevel.objects.filter(
            id=self.request.GET.get('adm_id')
        ).first()
        if admin_level is None:
            return Investment.objects.none()

        village_ids = admin_level.get_descendant_village_ids()
        return Investment.objects.filter(
            administrative_level_id__in=village_ids
        ).select_related(
            'administrative_level', 'funded_by', 'component', 'group_investment'
        ).annotate(
            status_order=Case(
                When(project_status=Investment.NOT_FUNDED, then=0),
                When(project_status=Investment.PAUSED, then=1),
                When(project_status=Investment.FUNDED, then=2),
                When(project_status=Investment.IN_PROGRESS, then=3),
                When(project_status=Investment.COMPLETED, then=4),
                output_field=IntegerField(),
            )
        ).order_by('status_order', 'ranking')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        package = Package.objects.get_active_cart(user=self.request.user)
        context['cart_items_id'] = set(
            package.funded_investments.values_list('id', flat=True)
        )
        return context

    @action(detail=False, methods=['POST'], url_path='cart-toggle', url_name='cart_toggle')
    def cart_toggle(self, request, *args, **kwargs):
        investment = Investment.objects.filter(id=request.data.get('investment_id')).first()
        if investment is None:
            return Response({'error': 'not_found'}, status=404)

        package = Package.objects.get_active_cart(user=request.user)
        already_in_cart = package.funded_investments.filter(id=investment.id).exists()
        # Cf. AdministrativeLevelDetailView.post() : le retrait doit toujours
        # être possible pour un investissement déjà dans CE panier, même si
        # son project_status est passé à FUNDED entre-temps (signal
        # m2m_changed dès l'ajout).
        if already_in_cart:
            package.funded_investments.remove(investment)
            track_user_activity(request, 'RemoveInvestmentInPackage')
            in_cart = False
        elif investment.project_status == Investment.NOT_FUNDED:
            package.funded_investments.add(investment)
            track_user_activity(request, 'AddInvestmentInPackage')
            in_cart = True
        else:
            in_cart = already_in_cart

        return Response({'investment_id': investment.id, 'in_cart': in_cart})


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
        subpopulation = request.GET.get('subpopulation-filter', None)
        priorities_filter = request.GET.get('priorities-filter', None)
        climate_contribution = request.GET.get('climate-contribution-filter', None)
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
            filters &= Q(funded_by__organization__id=organization)
        if sector and sector is not None:
            sector_type_list = list(Sector.objects.filter(category=sector).values('id', 'name'))
            sector_filter_active = True
            filters &= Q(sector__category=sector)
        if sector_type and sector_type is not None:
            filters &= Q(sector=sector_type)
        if subpopulation and subpopulation is not None:
            filters &= Q(**{subpopulation: True})
        if priorities_filter and priorities_filter is not None:
            priorities = [1]
            if priorities_filter == '2':
                priorities.append(2)
            elif priorities_filter == '3':
                priorities.append(2)
                priorities.append(3)
            filters &= Q(ranking__in=priorities)
        if climate_contribution and climate_contribution is not None:
            filters &= Q(climate_contribution=climate_contribution)

        investments = investments.filter(filters)
        investments = apply_climate_filters(investments, request.GET)

        # Calculate statistics
        total_communities = investments.values('administrative_level').distinct().count()
        total_investments = investments.count()
        total_subprojects = investments.exclude(funded_by=None).count()
        subprojects = investments.filter(investment_status=Investment.SUBPROJECT)
        total_completed_infrastructure = investments.filter(project_status=Investment.COMPLETED).count()
        total_funded_priorities = investments.filter(investment_status=Investment.PRIORITY, funded_by__isnull=False).count()
        total_unfunded_priorities = investments.filter(investment_status=Investment.PRIORITY,funded_by__isnull=True).count()

        # Calcul du montant total des priorités financées
        total_amount_funding = investments.filter(
            investment_status=Investment.PRIORITY,
            funded_by__isnull=False
        ).aggregate(total_funding=Sum('estimated_cost'))['total_funding'] or 0

        # Calcul du montant total des priorités non financées
        total_amount_unfunding = investments.filter(
            investment_status=Investment.PRIORITY,
            funded_by__isnull=True
        ).aggregate(total_unfunding=Sum('estimated_cost'))['total_unfunding'] or 0

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
            'description',
            'project_status',
            'administrative_level__id',
            'administrative_level__name',
            'administrative_level__parent__name',
            'administrative_level__parent__parent__name',
            'administrative_level__parent__parent__parent__name',
            'administrative_level__parent__parent__parent__parent__name',
            'latitude',
            'longitude',
            'sector__name',
            'sector__category__name',
            'physical_execution_rate'
        )

        # Filter out subprojects with NaN latitude or longitude
        filtered_subprojects = [
            subproject for subproject in subprojects_with_coordinates
            if not (math.isnan(subproject['latitude']) or math.isnan(subproject['longitude']))
        ]
        
        images_extensions_query = Q()
        for ext in IMAGE_EXTENSIONS:
            images_extensions_query |= Q(url__icontains=ext)

        for subproject in filtered_subprojects:
            # Chercher des photos dans les moments du processus,
            # en priorisant : Achevé > En cours
            attachments = []
            for moment in [
                Attachment.COMPLETED_INFRASTRUCTURE,
                Attachment.INFRASTRUCTURE_IN_PROGRESS,
            ]:
                attachments = list(
                    Attachment.objects.filter(
                        investment__id=subproject['id'],
                        process_moment=moment,
                    ).filter(images_extensions_query)
                    .values_list('url', flat=True)[:3]
                )
                if attachments:
                    break  # On a trouvé des photos, inutile de chercher plus loin

            if attachments:
                subproject['attachments'] = attachments

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
            'total_amount_funding': total_amount_funding,  # Montant total financé
            'total_amount_unfunding': total_amount_unfunding,  # Montant total non financé
        }

        return JsonResponse(data)
