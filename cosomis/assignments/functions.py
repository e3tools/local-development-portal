from .models import AssignAdministrativeLevelToFacilitator
from administrativelevels.models import AdministrativeLevel
from subprojects.models import Subproject
from cosomis.types import _QS

def get_subprojects_by_facilitator_id_and_project_id(facilitator_id, project_id) -> _QS:
    assigns_to_facilitator = AssignAdministrativeLevelToFacilitator.objects.filter(
        facilitator_id=facilitator_id, project_id=project_id, activated=True
    )

    subprojects = []
    for assign in assigns_to_facilitator:
        if assign.administrative_level and assign.administrative_level.cvd and \
            assign.administrative_level.cvd.headquarters_village and \
            assign.administrative_level.cvd.headquarters_village.id == assign.administrative_level.id:
            for subproject in assign.administrative_level.get_list_subprojects():
                if project_id in subproject.get_projects_ids():
                    subprojects.append(subproject)

    return Subproject.objects.filter(pk__in=[s.pk for s in subprojects])

def get_administrativelevels_by_facilitator_id_and_project_id(facilitator_id, project_id, type_adl="Village", parent_id=None) -> _QS:
    assigns_to_facilitator = AssignAdministrativeLevelToFacilitator.objects.filter(
        facilitator_id=facilitator_id, project_id=project_id, activated=True
    )
    
    administrativelevels = [assign.administrative_level for assign in assigns_to_facilitator if assign.administrative_level and (not parent_id or (parent_id and assign.administrative_level.parent and assign.administrative_level.parent_id==parent_id))]
    
    if type_adl in ("Village", "Canton"):
        if type_adl == "Canton":
            administrativelevels = list(set([adl.parent for adl in administrativelevels if adl.parent and (not parent_id or (parent_id and adl.parent.parent and adl.parent.parent_id==parent_id))]))
    else:
        administrativelevels = []

    return AdministrativeLevel.objects.filter(pk__in=[a.pk for a in administrativelevels])
