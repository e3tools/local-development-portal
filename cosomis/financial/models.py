from django.db import models
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel
from subprojects.models import Project
from cosomis.customers_fields import CustomerFloatRangeField


class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add = True, blank=True, null=True)
    updated_date = models.DateTimeField(auto_now = True, blank=True, null=True)

    class Meta:
        abstract = True
    
    def save_and_return_object(self):
        super().save()
        return self
    
class AdministrativeLevelAllocation(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, verbose_name=_("Administrative level"))
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    amount = CustomerFloatRangeField(verbose_name=_("Amount"), min_value=0)
    allocation_date = models.DateField(verbose_name=_("Date"))
    description = models.TextField(verbose_name=_("Description"))

