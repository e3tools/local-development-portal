from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password

from django import forms
from django.contrib import admin
# Create your models here.

class UserPassCode(models.Model):
    pass_code = models.CharField(max_length=128)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.user.__str__()

class UserPassCodeForm(forms.ModelForm):
    class Meta:
        model = UserPassCode
        exclude = []

class UserPassCodeAdmin(admin.ModelAdmin):
    form = UserPassCodeForm
    list_display = ['user', 'pass_code']

    def save_model(self, request, obj, form, change):
        obj.pass_code = make_password(obj.pass_code)
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if hasattr(obj, "pass_code"):
            return ['pass_code']
        return self.readonly_fields

admin.site.register(UserPassCode, UserPassCodeAdmin)
