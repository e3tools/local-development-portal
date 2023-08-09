from subprojects.models import Subproject, Component
from no_sql_client import NoSQLClient
from authentication.models import Facilitator
from administrativelevels.models import AdministrativeLevel
from assignments.models import AssignAdministrativeLevelToFacilitator


def get_facilitators_village_liste(develop_mode=False, training_mode=False, no_sql_db=False, only_ids=True):
    administrative_levels = []
    nsc = NoSQLClient()
    if no_sql_db:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode, no_sql_db_name=no_sql_db)
    else:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode)
    for f in facilitators:
        facilitator_db = nsc.get_db(f.no_sql_db_name)
        # docs = facilitator_db.all_docs(include_docs=True)['rows']
        docs = facilitator_db.get_query_result({"type": 'facilitator'})[:]
        
        if docs:
            # for _doc in docs:
            # doc = _doc.get('doc')
            doc = facilitator_db[docs[0]['_id']]
            # if doc.get('type') == 'facilitator':
            for ad in doc.get('administrative_levels'):
                if only_ids:
                    administrative_levels.append(ad.get('id'))
                else:
                    administrative_levels.append(ad)
    return administrative_levels

def attribute_component_to_subprojects(subprojects, component):
    print("Start !")
    for subproject in subprojects:
        print(subproject.full_title_of_approved_subproject)
        subproject.component = component
        subproject.save()
    print()
    print("Done !")

def delete_administrative_levels_who_are_not_children(ads, _type):
    if _type != "Village":
        for ad in ads.filter(type=_type):
            if len(list(ad.administrativelevel_set.get_queryset())) == 0:
                ad.delete()

def delete_administrative_levels_who_are_not_attribute_to_facilitator():
    facilitators_village_liste = get_facilitators_village_liste()

    print("Start")
    print()
    ads = AdministrativeLevel.objects.all()

    print("Village")
    for ad in ads.filter(type="Village"):
        if str(ad.id) not in facilitators_village_liste:
            ad.delete()

    print("Canton")
    delete_administrative_levels_who_are_not_children(ads, "Canton")

    print("Commune")
    delete_administrative_levels_who_are_not_children(ads, "Commune")

    print("Prefecture")
    delete_administrative_levels_who_are_not_children(ads, "Prefecture")

    print("Region")
    delete_administrative_levels_who_are_not_children(ads, "Region")

    print()
    print("Done !")

def delete_administrative_levels_who_are_not_id_in_sql_db():
    nsc = NoSQLClient()
    adm_db = nsc.get_db("administrative_levels")
    docs = adm_db.all_docs(include_docs=True)['rows']
    count = 0
    for _doc in docs:
        doc = _doc.get('doc')
        if doc.get('type') == 'administrative_level' and doc.get('administrative_id') and doc.get('administrative_id') != "1":
            try:
                AdministrativeLevel.objects.get(id=int(doc.get('administrative_id')))
            except AdministrativeLevel.DoesNotExist:
                administrative_level = adm_db[doc.get('_id')]
                print(administrative_level)
                administrative_level.delete()
                count += 1
    print(count)



def attribute_project_to_subprojects(subprojects, project):
    print("Start !")
    for subproject in subprojects:
        print(subproject.full_title_of_approved_subproject)
        subproject.projects.add(project)
        subproject.save()
    print()
    print("Done !")



def save_facilitator_assignment_in_mis(project_id: int, develop_mode=False, training_mode=False, no_sql_db=False):
    print(">>> Start!")
    nsc = NoSQLClient()
    if no_sql_db:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode, no_sql_db_name=no_sql_db)
    else:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode)
    for f in facilitators:
        facilitator_db = nsc.get_db(f.no_sql_db_name)
        docs = facilitator_db.get_query_result({"type": 'facilitator'})[:]
        
        if docs:
            doc = facilitator_db[docs[0]['_id']]
            print(doc)
            for ad in doc.get('administrative_levels'):
                id_str = ad.get('id')
                if (id_str and str(id_str).isdigit() and \
                    not AssignAdministrativeLevelToFacilitator.objects.filter(administrative_level_id=int(id_str), project_id=project_id, activated=True)):
                    try:
                        assign = AssignAdministrativeLevelToFacilitator()
                        assign.administrative_level_id = int(id_str)
                        assign.facilitator_id = str(f.id)
                        assign.project_id = project_id
                        assign.save()
                    except Exception as exc:
                        print(exc)
                        input()
    print(">>> Done!")


def link_infrastures_to_subproject():
    print("Start !")
    subprojects = Subproject.objects.all().order_by('number', 'joint_subproject_number')
    for subproject in subprojects:
        for _subproject in subprojects:
            if subproject.id != _subproject.id and \
                subproject.number < _subproject.number and \
                    subproject.joint_subproject_number == _subproject.joint_subproject_number:
                print(_subproject.full_title_of_approved_subproject)
                _subproject.link_to_subproject = subproject
                _subproject.subproject_type_designation = "Infrastructure"
                _subproject.save()
    print()
    print("Done !")