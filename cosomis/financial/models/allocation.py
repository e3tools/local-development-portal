from django.db import models
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel, CVD
from subprojects.models import Project
from cosomis.customers_fields import CustomerFloatRangeField
from cosomis.models_base import BaseModel


    
class AdministrativeLevelAllocation(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, verbose_name=_("Administrative level"), null=True, blank=True)
    cvd = models.ForeignKey(CVD, on_delete=models.CASCADE, verbose_name=_("CVD"), null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    amount = CustomerFloatRangeField(verbose_name=_("Amount"), min_value=0)
    allocation_date = models.DateField(verbose_name=_("Date"), null=True, blank=True)
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    
    class Meta(object):
        app_label = 'financial'
        db_table = 'financial_administrativeLevel_allocation'
