from django.contrib import admin
from .models import Subproject, VulnerableGroup

# Register your models here.
admin.site.register(Subproject)
admin.site.register(VulnerableGroup)