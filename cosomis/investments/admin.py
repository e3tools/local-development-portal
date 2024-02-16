from django.contrib import admin
from .models import Investment, Sector, Category, Package


admin.site.register(Investment)
admin.site.register(Sector)
admin.site.register(Category)
admin.site.register(Package)
