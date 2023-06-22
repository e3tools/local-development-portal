from subprojects.models import Subproject, Component
from no_sql_client import NoSQLClient
from authentication.models import Facilitator
from administrativelevels.models import AdministrativeLevel


def get_facilitators_village_liste(develop_mode=False, training_mode=False, no_sql_db=False, only_ids=True):
    administrative_levels = []
    nsc = NoSQLClient()
    if no_sql_db:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode, no_sql_db_name=no_sql_db)
    else:
        facilitators = Facilitator.objects.using('cdd').filter(develop_mode=develop_mode, training_mode=training_mode)
    for f in facilitators:
        facilitator_db = nsc.get_db(f.no_sql_db_name)
        docs = facilitator_db.all_docs(include_docs=True)['rows']
        
        for _doc in docs:
            doc = _doc.get('doc')
            if doc.get('type') == 'facilitator':
                for ad in doc.get('administrative_levels'):
                    if only_ids:
                        administrative_levels.append(ad.get('id'))
                    else:
                        administrative_levels.append(ad)

def attribute_component_to_subprojects(subprojects, component):
    print("Start !")
    for subproject in subprojects:
        print(subproject.name)
        subproject.component = component
        subproject.save()
    print()
    print("Done !")


def delete_administrative_levels_who_are_not_attribute_to_facilitator():
    facilitators_village_liste = get_facilitators_village_liste()

    print("Start")
    for ad in AdministrativeLevel.objects.all():
        if str(ad.id) not in facilitators_village_liste:
            ad.delete()

    print()
    print("Done !")

    