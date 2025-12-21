from django.contrib.auth.models import User
from django.db.models import Q

from investments.domain.criterias.investment_criteria import InvestmentCriteria
from investments.domain.criterias.package_criteria import PackageCriteria
from investments.models import Package, Investment


class DbPackagesRepository:
    def __init__(self):
        self.__model = Package.objects

    def find_by_criteria(self, criteria: PackageCriteria):
        filters_criteria: Q = self.__build_filter_criteria(criteria)
        return self.__model.filter(filters_criteria).order_by('ranking')

    def __build_filter_criteria(self, criteria: PackageCriteria) -> Q:
        q = Q()

        if criteria.id is not None:
            q = q & Q(id=criteria.id)

        if criteria.user_id is not None:
            q = q & Q(user=criteria.user_id)

        if criteria.status is not None:
            q = q & Q(user=criteria.status)

        return q

    def update_package_funded_investments(self, user: User, investment: Investment):
        package = Package.objects.get_active_cart(user=user)
        if package.funded_investments.filter(id=investment.id).exists():
            package.funded_investments.remove(investment)
        else:
            package.funded_investments.add(investment)

