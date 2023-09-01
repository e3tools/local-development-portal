from django.db import models
from administrativelevels.models import AdministrativeLevel
from django.utils.translation import gettext_lazy as _
from subprojects.models import Project

from cosomis.customers_fields import CustomerIntegerRangeField
from cosomis.models_base import BaseModel



class Wave(BaseModel):
    number = models.IntegerField(blank=False, null=False, verbose_name=_("Number"))
    description = models.TextField(blank=False, null=False, verbose_name=_("Description"))

    def __str__(self) -> str:
        return f'{self.number} : {self.description}'
    
    class Meta:
        unique_together = ['number']
        

class AdministrativeLevelWave(BaseModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    wave = models.ForeignKey(Wave, on_delete=models.CASCADE, verbose_name=_("Wave"))
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, verbose_name=_("Administrative level"))
    begin = models.DateField(blank=True, null=True, verbose_name=_("Begin"))
    end = models.DateField(blank=True, null=True, verbose_name=_("End"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    
    class Meta:
        unique_together = ['administrative_level', 'wave', 'project']
    

    def __str__(self) -> str:
        return f'{self.administrative_level} : {self.wave} : {self.project}'
    

class PeriodWave(BaseModel):
    part = CustomerIntegerRangeField(verbose_name=_("Part"), min_value=1)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name=_("Project"))
    wave = models.ForeignKey("Wave", on_delete=models.CASCADE, verbose_name=_("Wave"))
    administrative_levels = models.ManyToManyField(AdministrativeLevelWave, default=[], verbose_name=_("Administrative level"))
    begin = models.DateField(verbose_name=_("Begin"))
    end = models.DateField(verbose_name=_("End"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))

    def __str__(self) -> str:
        return f'{self.begin} {_("at")} {self.end} : {self.wave} : {self.project}'
    
