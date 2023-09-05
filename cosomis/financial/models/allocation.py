from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum

from administrativelevels.models import AdministrativeLevel, CVD
from subprojects.models import Project, Component
from cosomis.customers_fields import CustomerFloatRangeField
from cosomis.models_base import BaseModel


    
class AdministrativeLevelAllocation(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, verbose_name=_("Administrative level"), null=True, blank=True)
    cvd = models.ForeignKey(CVD, on_delete=models.CASCADE, verbose_name=_("CVD"), null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    component = models.ForeignKey(Component, on_delete=models.CASCADE, verbose_name=_("Component (Subcomponent)"), null=True)
    amount = CustomerFloatRangeField(verbose_name=_("Amount allocated"), min_value=0)
    amount_in_dollars = CustomerFloatRangeField(verbose_name=_("Amount allocated in dollars"), min_value=0)
    allocation_date = models.DateField(verbose_name=_("Date"), null=True, blank=True)
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    
    class Meta(object):
        app_label = 'financial'
        db_table = 'financial_administrativeLevel_allocation'


    def sum_amount_by_administrative_level(self):
        return AdministrativeLevelAllocation.objects.filter(
            administrative_level_id=self.administrative_level.id
        ).aggregate(Sum('amount'))['amount__sum']

    def sum_amount_in_dollars_by_administrative_level(self):
        return AdministrativeLevelAllocation.objects.filter(
            administrative_level_id=self.administrative_level.id
        ).aggregate(Sum('amount_in_dollars'))['amount_in_dollars__sum']

    def sum_amount_by_administrative_level_and_component(self, component_id):
        return AdministrativeLevelAllocation.objects.filter(
            component_id=component_id, administrative_level_id=self.administrative_level.id
        ).aggregate(Sum('amount'))['amount__sum']

    def sum_amount_in_dollars_by_administrative_level_and_component(self, component_id):
        return AdministrativeLevelAllocation.objects.filter(
            component_id=component_id, administrative_level_id=self.administrative_level.id
        ).aggregate(Sum('amount_in_dollars'))['amount_in_dollars__sum']

