from django.contrib import admin
from .models import Investment, Sector, Category, Package, Attachment


admin.site.register(Investment)
admin.site.register(Sector)
admin.site.register(Category)
admin.site.register(Package)
admin.site.register(Attachment)
