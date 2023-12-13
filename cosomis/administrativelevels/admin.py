from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit, Phase, Activity, Task


admin.site.register(AdministrativeLevel)
admin.site.register(GeographicalUnit)
admin.site.register(Phase)
admin.site.register(Activity)
admin.site.register(Task)
