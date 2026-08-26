from rest_framework import serializers
from django.urls import reverse
from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from investments.models import Investment
from administrativelevels.models import AdministrativeLevel


def _safe_parent_chain(adm_level, depth):
    """Walk `depth` parents up, returning the final AdministrativeLevel or None."""
    node = adm_level
    for _i in range(depth):
        if node is None:
            return None
        node = node.parent
    return node


class InvestmentSerializer(serializers.ModelSerializer):

    select_input = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    administrative_level__type = serializers.SerializerMethodField()
    administrative_level__name = serializers.SerializerMethodField()
    administrative_level__parent__name = serializers.SerializerMethodField()
    administrative_level__parent__parent__name = serializers.SerializerMethodField()
    administrative_level__parent__parent__parent__name = serializers.SerializerMethodField()
    population_priority = serializers.SerializerMethodField()
    estimated_cost = serializers.SerializerMethodField()
    ranking = serializers.SerializerMethodField()
    administrative_level__type_with_projects_priority_came_from = serializers.SerializerMethodField()
    rejection_history = serializers.SerializerMethodField()


    class Meta:
        model = Investment
        fields = '__all__'

    def get_select_input(self, obj):
        checked = ' checked' if self.context.get('all_queryset') == 'true' else ''
        return format_html(
            '<label class="inv-checkbox"><input class="project-table-check" '
            'id="checkbox-{0}" value="{0}" type="checkbox"{1}><span></span></label>',
            obj.id, checked,
        )

    def get_title(self, obj):
        title = obj.title or ''
        description = obj.description or ''
        if title == 'Autre' and description:
            return format_html(
                '<a href="#" class="inv-title-link" data-container="body" '
                'data-toggle="popover" data-placement="top" data-trigger="hover" '
                'data-content="{1}"><span class="inv-title" title="{1}">{0} '
                '<span class="inv-title-extra">[{1}]</span></span></a>',
                title, description,
            )
        full = f"{title} {description}".strip() if description else title
        return format_html(
            '<span class="inv-title" title="{1}">{0}</span>',
            title, full,
        )

    def get_administrative_level__type(self, obj):
        return obj.administrative_level.type

    def get_administrative_level__name(self, obj):
        adm = obj.administrative_level
        if adm.type != AdministrativeLevel.VILLAGE:
            return "-"
        url = reverse('administrativelevels:village_detail', args=[adm.id])
        return format_html('<a class="inv-link inv-place" href="{}">{}</a>', url, adm.name)

    def get_administrative_level__parent__name(self, obj):
        parent = _safe_parent_chain(obj.administrative_level, 1)
        if parent.type == AdministrativeLevel.COMMUNE:
            parent = obj.administrative_level
        if parent is None:
            return format_html('<span class="inv-muted">—</span>')
        url = reverse('administrativelevels:canton_detail', args=[parent.id])
        return format_html(
            '<a class="inv-link inv-place" href="{}" target="_blank">{}</a>',
            url, parent.name,
        )

    def get_administrative_level__parent__parent__name(self, obj):
        node = _safe_parent_chain(obj.administrative_level, 2)
        if node.type == AdministrativeLevel.PREFECTURE:
            node = _safe_parent_chain(obj.administrative_level, 1)
        if node is None:
            return format_html('<span class="inv-muted">—</span>')
        return format_html('<span class="inv-place">{}</span>', node.name)

    def get_administrative_level__parent__parent__parent__name(self, obj):
        node = _safe_parent_chain(obj.administrative_level, 3)
        if node.type == AdministrativeLevel.REGION:
            node = _safe_parent_chain(obj.administrative_level, 2)
        if node is None:
            return format_html('<span class="inv-muted">—</span>')
        return format_html('<span class="inv-place">{}</span>', node.name)

    def get_population_priority(self, obj):
        chips = []
        # Use translated tooltips for each endorsement code
        if obj.endorsed_by_youth:
            chips.append(('J', _('Youth')))
        if obj.endorsed_by_women:
            chips.append(('F', _('Women')))
        if obj.endorsed_by_agriculturist:
            chips.append(('AG', _('Agriculturists')))
        if obj.endorsed_by_pastoralist:
            chips.append(('ME', _('Pastoralists')))
        if not chips:
            return format_html('<span class="inv-muted">—</span>')
        spans = format_html_join(
            '',
            '<span class="inv-endorse-chip inv-endorse-{0}" title="{1}">{0}</span>',
            chips,
        )
        return format_html('<span class="inv-endorse-wrap">{}</span>', spans)

    def get_estimated_cost(self, obj):
        if obj.estimated_cost is None or obj.estimated_cost < 1000000:
            return format_html(
                '<span class="inv-cost inv-cost-na">{}</span>', _('Not available')
            )
        amount = intcomma(obj.estimated_cost)
        return format_html(
            '<span class="inv-cost">{} <span class="inv-cost-currency">FCFA</span></span>',
            amount,
        )

    def get_ranking(self, obj):
        rank = obj.ranking
        if rank is None:
            return format_html('<span class="inv-rank-badge inv-rank-none">—</span>')
        cls_map = {1: 'inv-rank-1', 2: 'inv-rank-2', 3: 'inv-rank-3'}
        cls = cls_map.get(int(rank), 'inv-rank-other')
        return format_html(
            '<span class="inv-rank-badge {}" title="{}">{}</span>',
            cls, _('Village priority %(rank)s') % {'rank': rank}, rank,
        )

    def get_projects_priority_came_from(self, obj):
        return obj.get_projects_priority_came_from()

    def get_rejection_history(self, obj):
        rejection = obj.get_last_rejection()
        if not rejection:
            return format_html('<span class="inv-muted">—</span>')
        organization = rejection['organization'] or _('Unknown organization')
        reason = rejection['reason'] or _('No reason provided')
        return format_html(
            '<span class="badge badge-warning show-rejection-reason" style="cursor:pointer;" data-reason="{1}">'
            '{0}: {2} <i class="fas fa-info-circle"></i></span>',
            _('Previously rejected'), reason, organization,
        )

    def get_administrative_level__type_with_projects_priority_came_from(self, obj):
        adm_type = self.get_administrative_level__type(obj)
        priority_sources = self.get_projects_priority_came_from(obj)
        pill = format_html(
            '<span class="inv-source-pill">{}</span>', adm_type or '—'
        )
        if priority_sources:
            return format_html(
                '{0}<span class="inv-source-priority" title="{1}">{1}</span>',
                pill, priority_sources,
            )
        return pill