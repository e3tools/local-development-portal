from administrativelevels.models import AdministrativeLevel, CVD
from subprojects.models import VillagePriority, Component, Subproject
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from subprojects.functions import save_csv_datas_subprojects_in_db

import os
from sys import platform
from administrativelevels.libraries import functions as libraries_functions
from datetime import datetime
import pandas as pd
import copy




def get_value(elt):
    return elt if not pd.isna(elt) else None

def exists_id(liste, id):
    for o in liste:
        if o.id == id:
            return True
    return False


def save_csv_file_datas_in_db(datas_file: dict) -> str:
    """Function to save the CSV datas in database"""
    
    at_least_one_save = False # Variable to determine if at least one is saved
    at_least_one_error = False # Variable to determine if at least one error is occurred
    columns = ["Région", "Préfecture", "Commune", "Canton", "Village/localité"]
    if datas_file:
        count = 0
        long = len(list(datas_file.values())[0])
        while count < long:
            for column in columns:
                try:
                    name = str(datas_file[column][count]).upper().strip()
                    frontalier, rural, latitude, longitude = False, False, None, None
                    try:
                        frontalier = bool(get_value(datas_file["Village frontalier (1=oui, 0= non)"][count]))
                    except Exception as exc:
                        pass
                    try:
                        rural = bool(get_value(datas_file["Localité (Rural=1, urbain=0)"][count]))
                    except Exception as exc:
                        pass
                    try:
                        latitude = float(get_value(datas_file["Latitude"][count]))
                    except Exception as exc:
                        pass
                    try:
                        longitude = float(get_value(datas_file["Longitude"][count]))
                    except Exception as exc:
                        pass

                    _type = "Unknow"
                    parent_type = ()
                    if column == "Région":
                        _type = "Region"
                    elif column == "Préfecture":
                        _type = "Prefecture"
                        parent_type = ("Région", "Region")
                    elif column == "Commune":
                        _type = "Commune"
                        parent_type = ("Préfecture", "Prefecture")
                    elif column == "Canton":
                        _type = "Canton"
                        parent_type = ("Commune", "Commune")
                    elif column == "Village/localité":
                        _type = "Village"
                        parent_type = ("Canton", "Canton")

                    parent = None
                    try:
                        if _type not in ("Region", "Unknow"):
                            parent = AdministrativeLevel.objects.filter(name=str(datas_file[parent_type[0]][count]).upper().strip(), type=parent_type[1]).first() # Get the parent object of the administrative level
                    except Exception as exc:
                        pass
                    
                    if (_type not in ("Region", "Unknow") and parent) or _type == "Region":
                        administratives_levels = AdministrativeLevel.objects.filter(name=name, type=_type, parent=parent)
                        if not administratives_levels: # If the administrative level is not already save
                            administrative_level = AdministrativeLevel()
                            administrative_level.name = name
                            administrative_level.type = _type
                            administrative_level.parent = parent
                            # administrative_level.frontalier = frontalier
                            # administrative_level.rural = rural
                            # administrative_level.save()
                            at_least_one_save = True
                        else: #If the administrative level is already save
                            administrative_level = administratives_levels.first()
                            

                        administrative_level.frontalier = frontalier
                        administrative_level.rural = rural
                        administrative_level.latitude = latitude
                        administrative_level.longitude = longitude
                        administrative_level.save()
                    
                except Exception as exc:
                    at_least_one_error = True
                    print(exc)

            count += 1

    message = ""
    if at_least_one_save and not at_least_one_error:
        message = _("Success!")
    elif not at_least_one_save and not at_least_one_error:
        message = _("No items have been saved!")
    elif not at_least_one_save and at_least_one_error:
        message = _("A problem has occurred!")
    elif at_least_one_save and at_least_one_error:
        message = _("Some element(s) have not been saved!")

    return message



def get_administratives_levels_under_file_excel_or_csv(file_type="excel", params={"type":"All", "value_of_type":""}) -> str:
    _type = params.get("type").capitalize() if params.get("type") else ""
    if file_type not in ("csv", "excel") or _type not in ("All", "Region", "Prefecture", "Commune", "Canton", "Village"):
        return ""

    datas = {
        "Région" : {}, "Id Région" : {}, "Préfecture" : {}, "Id Préfecture" : {}, 
        "Commune" : {}, "Id Commune" : {}, "Canton" : {}, "Id Canton" : {}, 
        "Village/localité" : {}, "Id Village/localité" : {},
        "Village frontalier (1=oui, 0= non)" : {}, "Localité (Rural=1, urbain=0)" : {}, "Latitude" : {}, "Longitude" : {}
    }

    administratives_levels = []
    value_of_type = params.get("value_of_type").upper() if params.get("value_of_type") else ""
    if _type == "All":
        administratives_levels = AdministrativeLevel.objects.filter(type="Village")
    elif _type == "Region":
        for region in AdministrativeLevel.objects.filter(type=_type, name=value_of_type):
            for prefecture in AdministrativeLevel.objects.filter(parent=region):
                for commune in AdministrativeLevel.objects.filter(parent=prefecture):
                    for canton in AdministrativeLevel.objects.filter(parent=commune):
                        [administratives_levels.append(village) for village in canton.administrativelevel_set.get_queryset()]
    elif _type == "Prefecture":
        for prefecture in AdministrativeLevel.objects.filter(type=_type, name=value_of_type):
            for commune in AdministrativeLevel.objects.filter(parent=prefecture):
                for canton in AdministrativeLevel.objects.filter(parent=commune):
                    [administratives_levels.append(village) for village in canton.administrativelevel_set.get_queryset()]
    elif _type == "Commune":
        for commune in AdministrativeLevel.objects.filter(type=_type, name=value_of_type):
            for canton in AdministrativeLevel.objects.filter(parent=commune):
                [administratives_levels.append(village) for village in canton.administrativelevel_set.get_queryset()]
    elif _type == "Canton":
        for canton in AdministrativeLevel.objects.filter(type=_type, name=value_of_type):
            [administratives_levels.append(village) for village in canton.administrativelevel_set.get_queryset()]
    elif _type == "Village":
        administratives_levels = AdministrativeLevel.objects.filter(type=_type, name=value_of_type)

    count = 0
    for elt in administratives_levels:
        
        try:
            datas["Région"][count] = elt.parent.parent.parent.parent.name
            datas["Id Région"][count] = elt.parent.parent.parent.parent.pk
        except Exception as exc:
            datas["Région"][count] = None
            datas["Id Région"][count] = None
        
        try:
            datas["Préfecture"][count] = elt.parent.parent.parent.name
            datas["Id Préfecture"][count] = elt.parent.parent.parent.pk
        except Exception as exc:
            datas["Préfecture"][count] = None
            datas["Id Préfecture"][count] = None
        
        try:
            datas["Commune"][count] = elt.parent.parent.name
            datas["Id Commune"][count] = elt.parent.parent.pk
        except Exception as exc:
            datas["Commune"][count] = None
            datas["Id Commune"][count] = None
        
        try:
            datas["Canton"][count] = elt.parent.name
            datas["Id Canton"][count] = elt.parent.pk
        except Exception as exc:
            datas["Canton"][count] = None
            datas["Id Canton"][count] = None
        
        datas["Village/localité"][count] = elt.name
        datas["Id Village/localité"][count] = elt.pk
        datas["Village frontalier (1=oui, 0= non)"][count] = int(elt.frontalier)
        datas["Localité (Rural=1, urbain=0)"][count] = int(elt.rural)
        datas["Latitude"][count] = elt.latitude
        datas["Longitude"][count] = elt.longitude
        
        count += 1

    if not os.path.exists("media/"+file_type+"/administratives_levels"):
        os.makedirs("media/"+file_type+"/administratives_levels")

    file_name = "administratives_levels_" + _type.lower() + "_" + ((value_of_type.lower() + "_") if value_of_type else "")

    if file_type == "csv":
        file_path = file_type+"/administratives_levels/" + file_name + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") +".csv"
        pd.DataFrame(datas).to_csv("media/"+file_path)
    else:
        file_path = file_type+"/administratives_levels/" + file_name + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") +".xlsx"
        pd.DataFrame(datas).to_excel("media/"+file_path)

    if platform == "win32":
        # windows
        return file_path.replace("/", "\\\\")
    else:
        return file_path








def save_csv_datas_priorities_in_db(datas_file: dict, administrative_level_id=0, type_object="priority", cvd_ids=[], canton_ids=[]) -> str:
    """Function to save the CSV datas in database"""
    
    at_least_one_save = False # Variable to determine if at least one is saved
    at_least_one_error = False # Variable to determine if at least one error is occurred
    at_least_error_name = False # Variable to determine if the name of village is wrong
    text_errors = ""
    list_villages_not_found = []
    list_villages_multi_obj_found = []
    nbr_subproject_not_associate_to_priority = 0
    text_subproject_not_associate_to_priority = ""
    list_objects_exist = []
    nbr_other_errors = 0
    # columns = [
    #     "Canton", "Villages", "Sous-projets prioritaire de la sous-composante 1.1 (infrastructures communautaires)", 
    #     "Coût estimatif", "Cycle", "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"
    # ]
    columns = [
        "Sous-projets prioritaire de la sous-composante 1.1 (infrastructures communautaires)", 
        "Sous-projets prioritaire de la sous-composante 1.3 (Besoins des jeunes)"
    ]
    # print(list(datas_file.keys()))
    _components = {
        '1': 'COMPOSANTE 1', '1.1': 'COMPOSANTE 1.1', '1.2': 'COMPOSANTE 1.2', 
        '1.2a': 'COMPOSANTE 1.2a', '1.2b': 'COMPOSANTE 1.2b', '1.3': 'COMPOSANTE 1.3', 
        '2': 'COMPOSANTE 2', '3': 'COMPOSANTE 3', '4': 'COMPOSANTE 4', '5': 'COMPOSANTE 5'
    }
    
    if datas_file and type_object != "subproject_new":
        count = 0
        long = len(list(datas_file.values())[0])
        while count < long:
            for column in columns:
                
                try:
                    data = datas_file[column][count]
                    canton = datas_file["Canton"][count]
                    _village = str(datas_file["Villages"][count])
                    __village = str(datas_file["Villages"][count]).upper()
                    estimated_cost = datas_file["Coût estimatif"][count]
                    estimated_cost = estimated_cost if not pd.isna(estimated_cost) else None
                    cycle = datas_file["Cycle"][count]
                    cycle = cycle if not pd.isna(cycle) else None
                    ranking = 0
                    name_priority = None
                    component = None
                    
                    for village in __village.split("/"):
                        village = village.strip()
                        _is_object_error = False
                        administrative_level = None
                        try:
                            administrative_level = AdministrativeLevel.objects.get(name=village, type="Village")
                        except AdministrativeLevel.DoesNotExist as exc:
                            try:
                                administrative_level = AdministrativeLevel.objects.get(
                                    name=libraries_functions.strip_accents(village), type="Village"
                                )
                            except AdministrativeLevel.DoesNotExist as exc:
                                try:
                                    administrative_level = AdministrativeLevel.objects.get(name=village.replace(" ", ""), type="Village")
                                except AdministrativeLevel.DoesNotExist as exc:
                                    try:
                                        administrative_level = AdministrativeLevel.objects.get(
                                            name=libraries_functions.strip_accents(village.replace(" ", "")), type="Village"
                                        )
                                    except AdministrativeLevel.DoesNotExist as exc:
                                        _is_object_error = True
                                        if _village not in list_villages_not_found:
                                            list_villages_not_found.append(_village)
                                        text_errors += (f'\nLine N°{count} [{_village}]: {exc.__str__()}' if text_errors else f'Line N°{count}: {exc.__str__()}')
                                        at_least_error_name = True
                                        at_least_one_error = True
                                    except AdministrativeLevel.MultipleObjectsReturned as exc:
                                        raise AdministrativeLevel.MultipleObjectsReturned()

                                except AdministrativeLevel.MultipleObjectsReturned as exc:
                                    raise AdministrativeLevel.MultipleObjectsReturned()

                            except AdministrativeLevel.MultipleObjectsReturned as exc:
                                raise AdministrativeLevel.MultipleObjectsReturned()

                        except AdministrativeLevel.MultipleObjectsReturned as exc:
                            _is_object_error = True
                            if _village not in list_villages_multi_obj_found:
                                list_villages_multi_obj_found.append(_village)
                            at_least_error_name = True
                            at_least_one_error = True
                            text_errors += f'\nLine N°{count} [{_village}]: {exc.__str__()}'
                        
                        if not _is_object_error:
                            
                            if administrative_level_id and int(administrative_level.id) != int(administrative_level_id):
                                continue #Continue without save the object if the village is specific and the village current is different
                            
                            estimated_cost = float(estimated_cost) if estimated_cost else 0.0
                            
                            _list_chars = column.split(" ")
                            for char in _list_chars:
                                if char in list(_components.keys()):
                                    _list_data = str(data).split("-")
                                    if _list_data[0].isdigit():
                                        ranking = int(_list_data[0])
                                        name_priority = (str(data)[(len(_list_data[0])+1):]).strip()
                                    else:
                                        name_priority = str(data).strip()
                                    try:
                                        component = Component.objects.get(name=_components[char].upper())
                                    except Exception as exc:
                                        component = None
                            
                            if type_object=="priority" and not VillagePriority.objects.filter(name=name_priority, administrative_level=administrative_level, component=component):
                                priority = VillagePriority()
                                priority.name = name_priority
                                priority.administrative_level = administrative_level
                                priority.estimated_cost = estimated_cost
                                priority.component = component
                                priority.ranking = ranking
                                priority.proposed_men = 0
                                priority.proposed_women = 0
                                priority.meeting_id = 1
                                priority.climate_changing_contribution = ""
                                priority.save()
                                at_least_one_save = True
                            elif type_object == "priority":
                                list_objects_exist.append(name_priority)
                            elif type_object=="subproject" and not Subproject.objects.filter(short_name=name_priority, administrative_level=administrative_level, component=component):
                                
                                if estimated_cost and estimated_cost != 0:
                                    villages = VillagePriority.objects.filter(administrative_level=administrative_level, component=component, estimated_cost=estimated_cost)
                                    
                                    subproject = Subproject()
                                    subproject.short_name = name_priority
                                    subproject.administrative_level = administrative_level
                                    subproject.target_youth_beneficiaries = 0
                                    subproject.component = component
                                    subproject.ranking = 1
                                    subproject.allocation = estimated_cost
                                    if len(villages) == 0:
                                        nbr_subproject_not_associate_to_priority += 1
                                        text_subproject_not_associate_to_priority += f'\nN°{nbr_subproject_not_associate_to_priority} [{name_priority}] : Not found priority. Please assaociate the priority manually.'
                                    elif len(villages) == 1:
                                        subproject.target_female_beneficiaries = villages[0].proposed_women
                                        subproject.target_male_beneficiaries = villages[0].proposed_men

                                        subproject = subproject.save_and_return_object()
                                        subproject.priorities.add(villages[0])
                                        subproject.save()

                                        at_least_one_save = True
                                    elif len(villages) > 1:
                                        nbr_subproject_not_associate_to_priority += 1
                                        text_subproject_not_associate_to_priority += f'\nN°{nbr_subproject_not_associate_to_priority} [{name_priority}] : Found {len(villages)} priorities for this subprojects. Please assaociate the priority manually.'
                            
                            elif type_object == "subproject":
                                list_objects_exist.append(name_priority)


                except Exception as exc:
                    text_errors += f'\nLine N°{count} [{_village}]: {exc.__str__()}'
                    nbr_other_errors += 1
                    at_least_one_error = True

            count += 1
            # if count == 1:
            #     break
            
    elif type_object == "subproject_new":
        return save_csv_datas_subprojects_in_db(datas_file, cvd_ids, canton_ids)
    
    message = ""
    if at_least_one_save and not at_least_one_error:
        message = _("Success!")
    elif not at_least_one_save and not at_least_one_error:
        message = _("No items have been saved!")
    elif not at_least_one_save and at_least_one_error:
        if at_least_error_name:
            message = _("A problem has occurred! The name(s) of the village(s) is wrong.")
        else:
            message = _("A problem has occurred!")
    elif at_least_one_save and at_least_one_error:
        if at_least_error_name:
            message = _("Some element(s) have not been saved! The name(s) of the village(s) is wrong.")
        else:
            message = _("Some element(s) have not been saved!")

    summary_errors = "##########################################################Summary###################################################################\n"
    summary_errors += f'\nNumber of object not found errors: {len(list_villages_not_found)} ==> {list_villages_not_found}'
    summary_errors += f'\n\nNumber of Multiple object found errors: {len(list_villages_multi_obj_found)} ==> {list_villages_multi_obj_found}'
    summary_errors += f'\n\nNumber of other errors: {nbr_other_errors}'

    if text_subproject_not_associate_to_priority:
        summary_errors += "\n\n\n##########################################################Object Subproject don't save###################################################################\n"
        summary_errors += f"\nNumber of the subprojects don't save : {nbr_subproject_not_associate_to_priority}"
        summary_errors += text_subproject_not_associate_to_priority

    if list_objects_exist:
        summary_errors += "\n\n\n##########################################################Object already exist###################################################################\n"
        summary_errors += f"\nNumber : {len(list_objects_exist)}"
        summary_errors += f"\n{list_objects_exist}"

    summary_errors += "\n\n\n##########################################################Messages###################################################################\n"
    summary_errors += "\n" + message

    summary_errors += "\n\n\n##########################################################Details###################################################################\n"
    summary_errors += "\n" + text_errors

    if not os.path.exists("media/logs/errors"):
        os.makedirs("media/logs/errors")
    file_path = "logs/errors/upload_priorities_logs_errors_" + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") + ".txt"
    
    if type_object=="subproject":
        file_path = file_path.replace("upload_priorities_logs_errors_", "upload_subprojects_logs_errors_")

    f = open("media/"+file_path, "a")
    f.write(summary_errors)
    f.close()
    


    return (message, file_path.replace("/", "\\\\") if platform == "win32" else file_path)

