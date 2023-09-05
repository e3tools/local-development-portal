from django.db import models
from django.utils.translation import gettext_lazy as _
from cosomis.models_base import BaseModel



class Bank(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    abbreviation = models.CharField(max_length=255, verbose_name=_("Abbreviation"))
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    class Meta(object):
        app_label = 'financial'
        db_table = 'financial_bank'
        unique_together = [['name'], ['abbreviation']]

    
    def __str__(self):
        return self.abbreviation