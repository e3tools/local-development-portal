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