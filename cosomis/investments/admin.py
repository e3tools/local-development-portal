from django.contrib import admin
from .models import Investment, Organization, Sector, Category


admin.site.register(Investment)
admin.site.register(Organization)
admin.site.register(Sector)
admin.site.register(Category)
