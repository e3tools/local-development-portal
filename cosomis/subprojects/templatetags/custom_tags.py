from django import template
from django.utils.translation import gettext_lazy

register = template.Library()



@register.filter(name="imgAWSS3Filter")
def img_aws_s3_filter(uri):
    return uri.split("?")[0]

@register.filter(name='has_group') 
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists() 

@register.filter(name='get_group_high') 
def get_group_high(user):
    """
    All Groups permissions
        - SuperAdmin        : 
        - CDD Specialist    : CDDSpecialist
        - Admin             : Admin
        - Evaluator         : Evaluator
        - Accountant        : Accountant
    """
    if user.is_superuser:
        return gettext_lazy("Principal Administrator").__str__()
    
    if user.groups.filter(name="Admin").exists():
        return gettext_lazy("Administrator").__str__()
    if user.groups.filter(name="CDDSpecialist").exists():
        return gettext_lazy("CDD Specialist").__str__()
    if user.groups.filter(name="Evaluator").exists():
        return gettext_lazy("Evaluator").__str__()
    if user.groups.filter(name="Accountant").exists():
        return gettext_lazy("Accountant").__str__()


    return gettext_lazy("User").__str__()