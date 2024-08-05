from django.contrib import admin
from .models import Investment, Package, Attachment


class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("title", "get_administrative_level_name", "sector", "investment_status", "project_status")
    search_fields = ("title", "administrative_level__name","investment_status")
    def get_administrative_level_name(self, obj):
        return obj.administrative_level.name
    get_administrative_level_name.short_description = 'Administrative Level'

admin.site.register(Investment, InvestmentAdmin)
admin.site.register(Package)
admin.site.register(Attachment)
