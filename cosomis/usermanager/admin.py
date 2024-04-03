from django.contrib.auth.hashers import make_password, check_password

from django import forms
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.contrib import admin
from .forms import UserCreationForm, UserChangeForm

from .models import UserPassCode, Organization, User


class UserCustomAdmin(UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ('email', 'username', 'date_joined', 'last_login', 'is_staff', )
    search_fields = ('email', 'username')
    readonly_fields = ('date_joined', 'last_login')

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)


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
admin.site.register(Organization)
admin.site.register(User, UserCustomAdmin)
