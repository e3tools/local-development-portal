from django.db import models
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel
from subprojects.models import Project
from cosomis.customers_fields import CustomerFloatRangeField
from cosomis.models_base import BaseModel


    
class AdministrativeLevelAllocation(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, verbose_name=_("Administrative level"))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    amount = CustomerFloatRangeField(verbose_name=_("Amount"), min_value=0)
    allocation_date = models.DateField(verbose_name=_("Date"))
    description = models.TextField(verbose_name=_("Description"))

    
    class Meta(object):
        app_label = 'financial'
        db_table = 'financial_administrativeLevel_allocation'
