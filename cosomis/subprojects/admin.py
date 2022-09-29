from django.contrib import admin
from .models import Subproject, CommunityPriority, VulnerableGroup

# Register your models here.
admin.site.register(Subproject)
admin.site.register(CommunityPriority)
admin.site.register(VulnerableGroup)