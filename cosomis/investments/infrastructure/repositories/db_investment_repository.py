from django.db.models import Q

from investments.domain.investment_criteria import InvestmentCriteria
from investments.models import Investment


class DbInvestmentRepository:
    def __init__(self):
        self.__investment_model = Investment.objects

    def find_by_criteria(self, investment_criteria: InvestmentCriteria):
        filters_criteria: Q = self.__build_filter_criteria(investment_criteria)
        return self.__investment_model.filter(filters_criteria).order_by('ranking')

    def __build_filter_criteria(self,investment_criteria: InvestmentCriteria) -> Q:
        q = Q()

        if investment_criteria.administrative_level is not None:
            q = q & Q(administrative_level=investment_criteria.administrative_level)

        return q
