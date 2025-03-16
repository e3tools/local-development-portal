from django.db.models import Q

from administrativelevels.domain.criterias.administrative_level_criteria import AdministrativeLevelCriteria
from administrativelevels.models import AdministrativeLevel


class DbAdministrativeLevelRepository:
    def __init__(self):
        self.__investment_model = AdministrativeLevel.objects

    def find_by_criteria(self, criteria: AdministrativeLevelCriteria):
        filters_criteria: Q = self.__build_filter_criteria(criteria)
        return self.__investment_model.filter(filters_criteria).order_by('rank')

    def __build_filter_criteria(self, criteria: AdministrativeLevelCriteria) -> Q:
        q = Q()

        if criteria.id is not None:
            q = q & Q(id=criteria.id)

        if criteria.type is not None:
            q = q & Q(id=criteria.type)

        if criteria.name is not None:
            q = q & Q(name__icontains=criteria.name)

        return q
