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
        - SuperAdmin            : 
        - CDD Specialist        : CDDSpecialist
        - Admin                 : Admin
        - Evaluator             : Evaluator
        - Accountant            : Accountant
        - Regional Coordinator  : RegionalCoordinator
        - National Coordinator  : NationalCoordinator
        - General Manager  : GeneralManager
        - Director  : Director
        - Advisor  : Advisor
        - Minister  : Minister
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
    if user.groups.filter(name="RegionalCoordinator").exists():
        return gettext_lazy("Regional Coordinator").__str__()
    if user.groups.filter(name="NationalCoordinator").exists():
        return gettext_lazy("National Coordinator").__str__()
    if user.groups.filter(name="GeneralManager").exists():
        return gettext_lazy("General Manager").__str__()
    if user.groups.filter(name="Director").exists():
        return gettext_lazy("Director").__str__()
    if user.groups.filter(name="Advisor").exists():
        return gettext_lazy("Advisor").__str__()
    if user.groups.filter(name="Minister").exists():
        return gettext_lazy("Minister").__str__()


    return gettext_lazy("User").__str__()

class MakeListNode(template.Node):
    def __init__(self, items, varname):
        self.items = items
        self.varname = varname

    def render(self, context):
        context[self.varname] = []
        for i in self.items:
            if i.isdigit():
                context[self.varname].append(int(i))
            else:
                context[self.varname].append(str(i).replace('"', ''))
        return ""
    
@register.tag
def make_list(parser, token):
    bits = list(token.split_contents())
    if len(bits) >= 4 and bits[-2] == "as":
        varname = bits[-1]
        items = bits[1:-2]
        return MakeListNode(items, varname)
    else:
        raise template.TemplateSyntaxError("%r expected format is 'item [item ...] as varname'" % bits[0])