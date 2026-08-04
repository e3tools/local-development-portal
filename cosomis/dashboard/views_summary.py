from django.conf import settings
from django.views import generic
from django.utils.translation import gettext_lazy as _
from cosomis.mixins import LoginRequiredApproveRequiredMixin
from usermanager.models import Organization
from administrativelevels.models import AdministrativeLevel, Sector, Category
from investments.models import Investment  # Make sure to import the Investment model
from investments.services import get_organization_account_stats
from static.config.datatable import get_datatable_config


class DashboardSummaryView(LoginRequiredApproveRequiredMixin, generic.TemplateView):
    template_name = "dashboard_summary.html"
    active_level1 = 'dashboard_summary'
    title = _('Dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['access_token'] = settings.MAPBOX_ACCESS_TOKEN
        context['lat'] = settings.DIAGNOSTIC_MAP_LATITUDE
        context['lng'] = settings.DIAGNOSTIC_MAP_LONGITUDE
        context['zoom'] = settings.DIAGNOSTIC_MAP_ZOOM
        context['ws_bound'] = settings.DIAGNOSTIC_MAP_WS_BOUND
        context['en_bound'] = settings.DIAGNOSTIC_MAP_EN_BOUND
        context['country_iso_code'] = settings.DIAGNOSTIC_MAP_ISO_CODE
        context.update(self.get_filters_context())
        context['project_statuses'] = Investment.PROJECT_STATUS_CHOICES

        organization_stats = get_organization_account_stats()
        context['organization_stats'] = organization_stats
        context['organization_stats_totals'] = {
            'total_accounts': sum(stat['total_accounts'] for stat in organization_stats),
            'approved_accounts': sum(stat['approved_accounts'] for stat in organization_stats),
            'total_investments': sum(stat['total_investments'] for stat in organization_stats),
        }
        context['active_organizations_count'] = sum(
            1 for stat in organization_stats if stat['organization_id'] is not None
        )
        context['datatable_config'] = get_datatable_config()
        return context

    def get_filters_context(self):
        filters_context = {}
        adm_queryset = AdministrativeLevel.objects.all()

        regions_qs = adm_queryset.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.REGION)
        )
        filters_context["regions"] = regions_qs
        # Hide the top-level dropdown when the dataset has a single root and
        # pre-load its prefectures so the cascade starts one level deeper.
        single_region = regions_qs.first() if regions_qs.count() == 1 else None
        filters_context["single_region"] = single_region
        filters_context["adm_labels"] = AdministrativeLevel.get_filter_labels()

        filters_context["prefectures"] = adm_queryset.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.PREFECTURE)
        )
        filters_context["communes"] = adm_queryset.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.COMMUNE)
        )
        filters_context["cantons"] = adm_queryset.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.CANTON)
        )
        filters_context["villages"] = adm_queryset.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE)
        )
        filters_context["organizations"] = Organization.objects.all()
        filters_context["sectors"] = Category.objects.all()
        filters_context["types"] = Investment.INVESTMENT_STATUS_CHOICES

        region_filter_id = self.request.GET.get("region-filter") or (
            str(single_region.id) if single_region else None
        )
        if region_filter_id:
            filters_context["prefectures"] = filters_context["prefectures"].filter(
                parent__id=region_filter_id
            )

        if "prefecture-filter" in self.request.GET:
            filters_context["communes"] = filters_context["communes"].filter(
                parent__id=self.request.GET["prefecture-filter"]
            )

        if "commune-filter" in self.request.GET:
            filters_context["cantons"] = filters_context["cantons"].filter(
                parent__id=self.request.GET["commune-filter"]
            )

        if "canton-filter" in self.request.GET:
            filters_context["villages"] = filters_context["villages"].filter(
                parent__id=self.request.GET["canton-filter"]
            )

        filters_context["query_strings_raw"] = self.request.GET.copy()

        filters_context["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {"id": "endorsed_by_pastoralist", "name": _("Endorsed by ethnic minorities")},
        ]
        return filters_context
