from django.contrib import admin

from process_manager.models import Wave, AdministrativeLevelWave, PeriodWave

admin.site.register([
    Wave, AdministrativeLevelWave, PeriodWave
])