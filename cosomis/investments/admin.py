from django.contrib import admin
from .models import Investment, InvestmentSectorChange, Package, Attachment


class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("title", "get_administrative_level_name", "sector", "funded_by", "investment_status", "project_status")
    search_fields = ("title", "administrative_level__name","investment_status")
    def get_administrative_level_name(self, obj):
        return obj.administrative_level.name
    get_administrative_level_name.short_description = 'Administrative Level'


class PackageAdmin(admin.ModelAdmin):
    list_display = ("status",)

class InvestmentSectorChangeAdmin(admin.ModelAdmin):
    """Read-only log of the corrections made on the category review page."""
    list_display = ("changed_at", "investment", "old_sector", "new_sector",
                    "old_estimated_cost", "new_estimated_cost", "changed_by", "undoes")
    list_filter = ("changed_at", "new_sector__category")
    search_fields = ("investment__title", "changed_by__email")
    list_select_related = ("investment", "old_sector", "new_sector", "changed_by", "undoes")
    date_hierarchy = "changed_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Investment, InvestmentAdmin)
admin.site.register(InvestmentSectorChange, InvestmentSectorChangeAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Attachment)
