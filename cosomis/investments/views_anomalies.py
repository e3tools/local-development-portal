from collections import defaultdict

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import generic

from cosomis.mixins import PageMixin, LoginRequiredApproveRequiredMixin
from usermanager.permissions import CanViewAnomaliesMixin, CanEditAnomaliesMixin
from administrativelevels.utils.functions import normalize_text
from .models import Investment, GroupInvestment
from .forms import InvestmentAnomalyEditForm, GroupInvestmentAnomalyEditForm

DISPLAY_LIMIT = 500
PAGE_SIZE = 15
GROUP_PAGE_SIZE = 5
NEAR_DUPLICATE_TITLE_THRESHOLD = 90

# Model types the delete/edit views are allowed to touch — never resolved
# from arbitrary user input, always looked up through this whitelist.
ANOMALY_DELETE_MODELS = {
    'investment': Investment,
    'groupinvestment': GroupInvestment,
}

ANOMALY_EDIT_FORMS = {
    'investment': InvestmentAnomalyEditForm,
    'groupinvestment': GroupInvestmentAnomalyEditForm,
}


class AnomaliesReportView(LoginRequiredApproveRequiredMixin, CanViewAnomaliesMixin, PageMixin, generic.TemplateView):
    """Vue de contrôle qualité des données synchronisées : recense les
    Investment/GroupInvestment mal ou partiellement rattachés, pour une revue
    manuelle. Chaque anomalie a son propre onglet, table paginée et bouton de
    suppression — aucune correction automatique n'est faite ici."""
    template_name = "investments/anomalies.html"
    title = _("Portal anomalies")
    active_level1 = 'anomalies'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        group_investments_no_canton = GroupInvestment.objects.filter(
            administrative_level__isnull=True
        ).select_related('component').order_by('title')
        group_investments_no_lieu = GroupInvestment.objects.filter(
            lieu__isnull=True
        ).select_related('component', 'administrative_level').order_by('title')
        investments_no_admin_level = Investment.objects.filter(
            administrative_level__isnull=True
        ).select_related('sector', 'component').order_by('title')
        investments_group_no_support = Investment.objects.filter(
            group_investment__isnull=False, administrative_levels__isnull=True
        ).select_related('administrative_level', 'group_investment', 'sector').order_by('title')

        duplicated_imported_ids = (
            Investment.objects.exclude(imported_project_id__isnull=True)
            .exclude(imported_project_id='')
            .values('imported_project_id')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
            .order_by('-total')
        )
        duplicated_imported_id_groups = [
            {
                'imported_project_id': row['imported_project_id'],
                'investments': list(
                    Investment.objects.filter(imported_project_id=row['imported_project_id'])
                    .select_related('administrative_level', 'sector', 'component', 'group_investment')
                ),
            }
            for row in duplicated_imported_ids[:DISPLAY_LIMIT]
        ]

        near_duplicate_group_investments = find_near_duplicates(
            GroupInvestment.objects.select_related('component', 'administrative_level'),
            key=lambda gi: gi.title,
            bucket=lambda gi: gi.component_id,
        )

        near_duplicate_investments = find_near_duplicates(
            Investment.objects.filter(group_investment__isnull=True)
            .select_related('administrative_level', 'sector', 'component'),
            key=lambda inv: f"{' '+inv.imported_project_id if inv.imported_project_id else ''}{inv.component.name+' ' if inv.component else ''}{inv.title}{' '+inv.description if inv.description else ''}{' '+inv.funded_by.name if inv.funded_by else ''}",
            bucket=lambda inv: (inv.administrative_level_id, inv.sector_id),
        )

        tabs = [
            {
                'key': 'no_canton',
                'label': _("GroupInvestment without a canton"),
                'icon': 'fa-map-marker-alt',
                'kind': 'groupinvestment_list',
                'items': group_investments_no_canton,
                'total': group_investments_no_canton.count(),
            },
            {
                'key': 'no_lieu',
                'label': _("GroupInvestment without a location"),
                'icon': 'fa-map-pin',
                'kind': 'groupinvestment_list',
                'items': group_investments_no_lieu,
                'total': group_investments_no_lieu.count(),
            },
            {
                'key': 'no_admin_level',
                'label': _("Investment without an administrative_level"),
                'icon': 'fa-exclamation-triangle',
                'kind': 'investment_list',
                'items': investments_no_admin_level,
                'total': investments_no_admin_level.count(),
            },
            {
                'key': 'no_support',
                'label': _("Market Investment without a supporting village"),
                'icon': 'fa-store-alt',
                'kind': 'investment_list',
                'items': investments_group_no_support,
                'total': investments_group_no_support.count(),
            },
            {
                'key': 'dup_imported_id',
                'label': _("Investment sharing the same imported_project_id"),
                'icon': 'fa-fingerprint',
                'kind': 'investment_groups',
                'items': duplicated_imported_id_groups,
                'total': duplicated_imported_ids.count(),
            },
            {
                'key': 'dup_group_investment',
                'label': _("GroupInvestment near-duplicates"),
                'icon': 'fa-clone',
                'kind': 'groupinvestment_pairs',
                'items': near_duplicate_group_investments[:DISPLAY_LIMIT],
                'total': len(near_duplicate_group_investments),
            },
            {
                'key': 'dup_investment',
                'label': _("Investment near-duplicates"),
                'icon': 'fa-copy',
                'kind': 'investment_pairs',
                'items': near_duplicate_investments[:DISPLAY_LIMIT],
                'total': len(near_duplicate_investments),
            },
        ]

        valid_keys = [tab['key'] for tab in tabs]
        requested_tab_key = self.kwargs.get('tab_key')
        if requested_tab_key is not None and requested_tab_key not in valid_keys:
            raise Http404
        active_tab_key = requested_tab_key or tabs[0]['key']

        for tab in tabs:
            tab['url'] = reverse('investments:anomalies_tab', kwargs={'tab_key': tab['key']})
            if tab['key'] != active_tab_key:
                continue
            page_param = f"page_{tab['key']}"
            # Each duplicated-imported-id "row" is itself a small table of
            # investments, so a full PAGE_SIZE of those per page would be a
            # wall of nested tables — page that one more tightly.
            page_size = GROUP_PAGE_SIZE if tab['kind'] == 'investment_groups' else PAGE_SIZE
            paginator = Paginator(tab['items'], page_size)
            page_number = self.request.GET.get(page_param) or 1
            tab['page_obj'] = paginator.get_page(page_number)
            tab['page_param'] = page_param

        context.update({
            'tabs': tabs,
            'active_tab_key': active_tab_key,
            'display_limit': DISPLAY_LIMIT,
            'can_edit_anomalies': self.request.user.is_superuser or self.request.user.is_anomaly_corrector,
            'current_path': self.request.get_full_path(),
        })
        return context


class AnomalyObjectDeleteView(CanEditAnomaliesMixin, generic.View):
    """Deletes one Investment or GroupInvestment row flagged on the anomalies
    report. Manual, one-object-at-a-time corrective action — no cascade
    beyond each model's own on_delete rules (e.g. an Investment losing its
    group_investment link just goes back to being ungrouped).

    Viewing the report is open to moderators too (CanViewAnomaliesMixin), but
    deleting is reserved for whoever can actually correct anomalies."""

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_anomaly_corrector):
            raise PermissionDenied
        model = ANOMALY_DELETE_MODELS.get(kwargs.get('model'))
        if model is None:
            raise Http404
        obj = get_object_or_404(model, pk=kwargs.get('pk'))
        label = str(obj)
        obj.delete()
        messages.success(
            request,
            _('"%(label)s" has been deleted.') % {'label': label},
            extra_tags='success',
        )
        next_url = request.POST.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        return redirect(reverse('investments:anomalies'))


class AnomalyObjectEditView(CanEditAnomaliesMixin, generic.View):
    """Edits one Investment or GroupInvestment row flagged on the anomalies
    report — the same corrective-action permission as deletion (superuser or
    is_anomaly_corrector; plain moderators can view but not touch data)."""
    template_name = "investments/anomaly_edit.html"

    def _get_object_and_form_class(self, **kwargs):
        model = ANOMALY_DELETE_MODELS.get(kwargs.get('model'))
        form_class = ANOMALY_EDIT_FORMS.get(kwargs.get('model'))
        if model is None or form_class is None:
            raise Http404
        obj = get_object_or_404(model, pk=kwargs.get('pk'))
        return obj, form_class

    def get(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_anomaly_corrector):
            raise PermissionDenied
        obj, form_class = self._get_object_and_form_class(**kwargs)
        form = form_class(instance=obj)
        return self._render(request, obj, form, **kwargs)

    def post(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.is_anomaly_corrector):
            raise PermissionDenied
        obj, form_class = self._get_object_and_form_class(**kwargs)
        form = form_class(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                _('"%(label)s" has been updated.') % {'label': str(obj)},
                extra_tags='success',
            )
            next_url = request.POST.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            return redirect(reverse('investments:anomalies'))
        return self._render(request, obj, form, **kwargs)

    def _render(self, request, obj, form, **kwargs):
        next_url = request.GET.get('next') or request.POST.get('next') or reverse('investments:anomalies')
        return render(request, self.template_name, {
            'object': obj,
            'form': form,
            'model_key': kwargs.get('model'),
            'next_url': next_url,
            'title': _("Edit %(label)s") % {'label': str(obj)},
        })


def find_near_duplicates(queryset, key, bucket):
    """Regroupe les objets par `bucket(obj)` puis compare deux à deux (au sein
    d'un même bucket seulement, pour rester rapide) les textes normalisés de
    `key(obj)` : retourne les paires dont la ressemblance dépasse le seuil,
    sans jamais les fusionner — juste pour les signaler à la revue manuelle."""
    from fuzzywuzzy import fuzz

    buckets = defaultdict(list)
    for obj in queryset:
        buckets[bucket(obj)].append(obj)

    pairs = []
    for items in buckets.values():
        if len(items) < 2:
            continue
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                score = fuzz.ratio(normalize_text(key(a)), normalize_text(key(b)))
                if score >= NEAR_DUPLICATE_TITLE_THRESHOLD:
                    pairs.append((a, b, score))
    pairs.sort(key=lambda p: -p[2])
    return pairs
