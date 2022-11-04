from administrativelevels.models import AdministrativeLevel
from django.utils.translation import gettext_lazy as _
import os
from sys import platform

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
                    name = str(datas_file[column][count]).upper()
                    frontalier = bool(datas_file["Village frontalier (1=oui, 0= non)"][count])
                    rural = bool(datas_file["Localité (Rural=1, urbain=0)"][count])
                    latitude, longitude = None, None
                    try:
                        latitude = float(datas_file["Latitude"][count])
                        longitude = float(datas_file["Longitude"][count])
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
                            parent = AdministrativeLevel.objects.get(name=str(datas_file[parent_type[0]][count]).upper(), type=parent_type[1]) # Get the parent object of the administrative level
                    except Exception as exc:
                        pass
                    
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

    from datetime import datetime
    import pandas as pd
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