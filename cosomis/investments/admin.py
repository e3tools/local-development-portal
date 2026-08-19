from django.contrib import admin
from .models import Investment, Package, Attachment, GroupInvestment


class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("title", "get_administrative_level_name", "sector", "component", "group_investment", "funded_by", "investment_status", "project_status")
    list_filter = ("component", "investment_status", "project_status")
    search_fields = ("title", "administrative_level__name","investment_status", "imported_project_id")
    def get_administrative_level_name(self, obj):
        return obj.administrative_level.name
    get_administrative_level_name.short_description = 'Administrative Level'


class GroupInvestmentAdmin(admin.ModelAdmin):
    list_display = ("title", "administrative_level", "lieu", "ranking", "component")
    list_filter = ("component",)
    search_fields = ("title",)


class PackageAdmin(admin.ModelAdmin):
    list_display = ("status",)

admin.site.register(Investment, InvestmentAdmin)
admin.site.register(GroupInvestment, GroupInvestmentAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Attachment)
