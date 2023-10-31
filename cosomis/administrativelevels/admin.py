from django.contrib import admin
from .models import AdministrativeLevel, GeographicalUnit, CVD, Category

# Register your models here.
admin.site.register(AdministrativeLevel)
admin.site.register(GeographicalUnit)
admin.site.register(CVD)
admin.site.register(Category)
