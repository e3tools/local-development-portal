from rest_framework import serializers
from django.urls import reverse
from django.contrib.humanize.templatetags.humanize import intcomma

from investments.models import Investment
from django.utils.translation import gettext_lazy as _


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
    administrative_level__type_with_projects_priority_came_from = serializers.SerializerMethodField()


    class Meta:
        model = Investment
        fields = '__all__'

    def get_select_input(self, obj):
        if 'all_queryset' in self.context and self.context['all_queryset'] == 'true':
            return '<input class="project-table-check" id="checkbox-' + str(obj.id) + '" value="' + str(
                obj.id) + '" type="checkbox" checked>'
        return '<input class="project-table-check" id="checkbox-' + str(obj.id) + '" value="' + str(
            obj.id) + '" type="checkbox">'

    def get_title(self, obj):
        if obj.title == 'Autre':
            description = obj.description if obj.description else '-'
            return ('<a '
                    'href="#" data-container="body" data-toggle="popover" '
                    'data-placement="top" data-trigger="hover" '
                    'data-content="{}">'
                    '{}'
                    '</a>').format(description, obj.title)
        else:
            return obj.title

    def get_administrative_level__type(self, obj):
        return obj.administrative_level.type

    def get_administrative_level__name(self, obj):
        url = reverse('administrativelevels:village_detail', args=[obj.administrative_level.id])
        return '<a href="{}">{}</a>'.format(url, obj.administrative_level.name)

    def get_administrative_level__parent__name(self, obj):
        return obj.administrative_level.parent.name

    def get_administrative_level__parent__parent__name(self, obj):
        return obj.administrative_level.parent.parent.name

    def get_administrative_level__parent__parent__parent__name(self, obj):
        return obj.administrative_level.parent.parent.parent.name

    def get_population_priority(self, obj):
        population_priority = list()
        if obj.endorsed_by_youth:
            population_priority.append('J')
        if obj.endorsed_by_women:
            population_priority.append('F')
        if obj.endorsed_by_agriculturist:
            population_priority.append('AG')
        if obj.endorsed_by_pastoralist:
            population_priority.append('ME')
        return ', '.join(population_priority)

    def get_estimated_cost(self, obj):
        if obj.estimated_cost < 1000000:
            return _('Not available')
        return intcomma(obj.estimated_cost)

    def get_projects_priority_came_from(self, obj):
        return obj.get_projects_priority_came_from()
    
    def get_administrative_level__type_with_projects_priority_came_from(self, obj):
        priority_sources = self.get_projects_priority_came_from(obj)
        if priority_sources:
            return f"{self.get_administrative_level__type(obj)} <br />({priority_sources})"
        return self.get_administrative_level__type(obj)