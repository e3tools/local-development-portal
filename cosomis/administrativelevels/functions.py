from administrativelevels.models import AdministrativeLevel
from django.utils.translation import gettext_lazy as _

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

                    if not AdministrativeLevel.objects.filter(name=name, type=_type, parent=parent): # If the administrative level is not already save
                        administrative_level = AdministrativeLevel()
                        administrative_level.name = name
                        administrative_level.type = _type
                        administrative_level.parent = parent
                        administrative_level.frontalier = frontalier
                        administrative_level.rural = rural
                        administrative_level.save()
                        at_least_one_save = True
                    
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