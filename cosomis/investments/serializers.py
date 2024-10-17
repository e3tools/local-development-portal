from rest_framework import serializers

from investments.models import Investment


class InvestmentSerializer(serializers.ModelSerializer):

    select_input = serializers.SerializerMethodField()
    administrative_level__type = serializers.SerializerMethodField()
    administrative_level__name = serializers.SerializerMethodField()
    administrative_level__parent__name = serializers.SerializerMethodField()
    administrative_level__parent__parent__name = serializers.SerializerMethodField()
    administrative_level__parent__parent__parent__name = serializers.SerializerMethodField()
    population_priority = serializers.SerializerMethodField()


    class Meta:
        model = Investment
        fields = '__all__'

    def get_select_input(self, obj):
        if 'all_queryset' in self.context and self.context['all_queryset'] == 'false':
            return '<input class="project-table-check" id="checkbox-' + str(obj.id) + '" value="' + str(obj.id) + '" type="checkbox">'
        return '<input class="project-table-check" id="checkbox-' + str(obj.id) + '" value="' + str(obj.id) + '" type="checkbox" checked>'

    def get_administrative_level__type(self, obj):
        return obj.administrative_level.type

    def get_administrative_level__name(self, obj):
        return obj.administrative_level.name

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

