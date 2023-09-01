from django.db import models
from django.utils.translation import gettext_lazy as _
from cosomis.models_base import BaseModel


# class BaseModel(models.Model):
#     created_date = models.DateTimeField(auto_now_add = True, blank=True, null=True)
#     updated_date = models.DateTimeField(auto_now = True, blank=True, null=True)

#     class Meta:
#         abstract = True
    
#     def save_and_return_object(self):
#         super().save()
#         return self

class Bank(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    abbreviation = models.CharField(max_length=255, verbose_name=_("Abbreviation"))
    description = models.TextField(verbose_name=_("Description"), null=True, blank=True)

    class Meta(object):
        app_label = 'financial'
        db_table = 'financial_bank'
