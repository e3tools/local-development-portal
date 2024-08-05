from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit, Phase, Activity, Task, Project, Sector, Category

class AdministrativeLevelAdmin(admin.ModelAdmin):
    list_display = ("name","type","parent")
    search_fields = ("name",)
admin.site.register(AdministrativeLevel, AdministrativeLevelAdmin)
admin.site.register(GeographicalUnit)
admin.site.register(Phase)
admin.site.register(Activity)
admin.site.register(Task)
admin.site.register(Project)
admin.site.register(Sector)
admin.site.register(Category)
