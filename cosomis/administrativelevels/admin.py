from django.contrib import admin
from .models import (
    AdministrativeLevel, GeographicalUnit, Phase, Activity, Task, Project, Sector, Category, GeoSegment,
    Component, GroupeSocioeconomique,
)

class AdministrativeLevelAdmin(admin.ModelAdmin):
    list_display = ("name","type","parent")
    search_fields = ("name",)

    fieldsets = [
        (
            "LDP options",
            {
                "fields": ["name", "rank", "rural", "frontalier", "status_color", "status_description", "total_population",
                           "population_men", "population_women", "population_young", "population_elder",
                           "population_handicap", "population_agriculturist", "population_pastoralist",
                           "population_minorities", "main_languages", "identified_priority", "infrastructure"],
            },
        ),
        (
            "System options",
            {
                "fields": ["parent", "type", "default_image", "facilitator", "no_sql_db_id"],
            },
        ),
        (
            "Climate options",
            {
                "fields": ["geographical_unit", "latitude", "longitude", "code_loc", "geo_segment"],
            },
        ),
    ]


admin.site.register(AdministrativeLevel, AdministrativeLevelAdmin)
admin.site.register(GeographicalUnit)
admin.site.register(Phase)
admin.site.register(Activity)
admin.site.register(Task)
admin.site.register(Project)
admin.site.register(Sector)
admin.site.register(Category)
admin.site.register(GeoSegment)


class ComponentAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "project", "parent")
    list_filter = ("project",)
    search_fields = ("name", "short_name")


class GroupeSocioeconomiqueAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


admin.site.register(Component, ComponentAdmin)
admin.site.register(GroupeSocioeconomique, GroupeSocioeconomiqueAdmin)
