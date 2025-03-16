from django.db.models import Q

from investments.domain.criterias.investment_criteria import InvestmentCriteria
from investments.models import Investment


class DbInvestmentRepository:
    def __init__(self):
        self.__model = Investment.objects

    def find_by_criteria(self, criteria: InvestmentCriteria):
        filters_criteria: Q = self.__build_filter_criteria(criteria)
        return self.__model.filter(filters_criteria).order_by('ranking')

    def __build_filter_criteria(self, criteria: InvestmentCriteria) -> Q:
        q = Q()

        if criteria.administrative_level_id is not None:
            q = q & Q(administrative_level=criteria.administrative_level_id)

        return q
