from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit, Phase, Activity, Task, Project, Sector, Category


admin.site.register(AdministrativeLevel)
admin.site.register(GeographicalUnit)
admin.site.register(Phase)
admin.site.register(Activity)
admin.site.register(Task)
admin.site.register(Project)
admin.site.register(Sector)
admin.site.register(Category)
