from cosomis.call_objects_from_other_db import cdd_objects_call

from process_manager.models import Wave, AdministrativeLevelWave
from subprojects.models import Project

def record_administrative_levels_waves():
    waves = cdd_objects_call.get_all_objects(Wave)
    administrative_levels_waves = cdd_objects_call.get_all_objects(AdministrativeLevelWave)

    Wave.objects.bulk_create([o for o in waves], ignore_conflicts=True)
    

    AdministrativeLevelWave.objects.bulk_create([
        AdministrativeLevelWave(
            project_id=o.project_id,
            wave_id=o.wave_id,
            administrative_level_id=o.administrative_level_id,
            begin=o.begin,
            end=o.end,
            description=o.description
        ) for o in administrative_levels_waves])