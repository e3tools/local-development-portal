from django.contrib import admin

from .models import AdministrativeLevelAllocation
# Register your models here.

class AdministrativeLevelAllocationAdmin(admin.ModelAdmin):
    fields = (
        'administrative_level',
        'project',
        'amount',
        'allocation_date',
        'description'
    )

    raw_id_fields = (
        'administrative_level',
    )
    list_display = (
        'id',
        'administrative_level',
        'project',
        'amount',
        'allocation_date'
    )
    search_fields = (
        'id',
        'administrative_level__name',
        'administrative_level__type',
        'project__name',
        'amount',
        'allocation_date',
        'description'
    )


admin.site.register(AdministrativeLevelAllocation, AdministrativeLevelAllocationAdmin)
