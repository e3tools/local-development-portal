from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit

# Register your models here.
admin.site.register(AdministrativeLevel)
admin.site.register(GeographicalUnit)
