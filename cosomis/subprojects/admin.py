from django.contrib import admin
from .models import Subproject, VulnerableGroup, VillagePriority, VillageMeeting, Component

# Register your models here.
admin.site.register(Subproject)
admin.site.register(VulnerableGroup)
admin.site.register(VillagePriority)
admin.site.register(VillageMeeting)
admin.site.register(Component)
