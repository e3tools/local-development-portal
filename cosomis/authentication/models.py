from django.db import models
from django.utils.translation import gettext_lazy as _

# from django.forms.models import model_to_dict

class Facilitator(models.Model):
    no_sql_user = models.CharField(max_length=150, unique=True)
    no_sql_pass = models.CharField(max_length=128)
    no_sql_db_name = models.CharField(max_length=150, unique=True)
    username = models.CharField(max_length=150, unique=True, verbose_name=_('username'))
    password = models.CharField(max_length=128, verbose_name=_('password'))
    code = models.CharField(max_length=6, unique=True, verbose_name=_('code'))
    active = models.BooleanField(default=False, verbose_name=_('active'))
    develop_mode = models.BooleanField(default=False, verbose_name=_('test mode'))
    training_mode = models.BooleanField(default=False, verbose_name=_('test mode'))
    
    name = models.CharField(max_length=200, null=True, blank=True, verbose_name=_('name'))
    email = models.CharField(max_length=100, null=True, blank=True, verbose_name=_('email'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('phone'))
    sex = models.CharField(max_length=5, null=True, blank=True, verbose_name=_('sex'))
    total_tasks = models.IntegerField(default=0)
    total_tasks_completed = models.IntegerField(default=0)
    last_activity = models.DateTimeField(blank=True, null=True)