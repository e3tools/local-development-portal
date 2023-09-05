from django.utils.translation import gettext_lazy as _
from django.db.models import Q
import os
from sys import platform
from datetime import datetime
import pandas as pd

from administrativelevels.models import CVD
from financial.models.bank import Bank


def get_value(elt):
    return elt if not pd.isna(elt) else None

def save_cvd_instead_of_csv_file_datas_in_db(datas_file: dict) -> str:
    """Function to save CVD instead of the CSV datas in database"""
    
    at_least_one_save = False # Variable to determine if at least one is saved
    at_least_one_error = False # Variable to determine if at least one error is occurred

    datas = {
        "REGION" : {}, "PREFECTURE" : {}, "COMMUNE" : {}, "CANTON" : {}, 
        "ID CVD": {}, "CVD": {}, "VILLAGES" : {}, "BANQUE": {}, "CODE BANQUE": {},
        "CODE GUICHET": {}, "N° DE COMPTE": {}, "RIB": {}, 
        "Nom du président du CVD": {}, "Tél du Président du CVD": {}, 
        "Nom du trésorier du CVD": {}, "Tél du trésorier du CVD": {}, 
        "Nom du secrétaire du CVD": {}, "Tél du secrétaire du CVD": {}
    }

    if datas_file:
        count = 0
        long = len(list(datas_file.values())[0])
        while count < long:
            try:
                cvd_id = get_value(datas_file["ID CVD"][count])
                bank = get_value(datas_file["BANQUE"][count])
                bank_code = get_value(datas_file["CODE BANQUE"][count])
                guichet_code = get_value(datas_file["CODE GUICHET"][count])
                account_number = get_value(datas_file["N° DE COMPTE"][count])
                rib = get_value(datas_file["RIB"][count])
                president_name_of_the_cvd, president_phone_of_the_cvd = None, None
                treasurer_name_of_the_cvd, treasurer_phone_of_the_cvd = None, None
                secretary_name_of_the_cvd, secretary_phone_of_the_cvd = None, None
                
                try:
                    president_name_of_the_cvd = get_value(datas_file["Nom du président du CVD"][count])
                except Exception as exc:
                    pass
                try:
                    president_phone_of_the_cvd = get_value(datas_file["Tél du Président du CVD"][count])
                except Exception as exc:
                    pass
                try:
                    treasurer_name_of_the_cvd = get_value(datas_file["Nom du trésorier du CVD"][count])
                except Exception as exc:
                    pass
                try:
                    treasurer_phone_of_the_cvd = get_value(datas_file["Tél du trésorier du CVD"][count])
                except Exception as exc:
                    pass
                try:
                    secretary_name_of_the_cvd = get_value(datas_file["Nom du secrétaire du CVD"][count])
                except Exception as exc:
                    pass
                try:
                    secretary_phone_of_the_cvd = get_value(datas_file["Tél du secrétaire du CVD"][count])
                except Exception as exc:
                    pass

                cvd = CVD.objects.filter(id=cvd_id).first()
                if cvd:
                    cvd.bank = Bank.objects.filter(Q(name=bank) | Q(abbreviation=bank)).first()
                    cvd.bank_code = bank_code
                    cvd.guichet_code = guichet_code
                    cvd.account_number = account_number
                    cvd.president_name_of_the_cvd = president_name_of_the_cvd
                    cvd.president_phone_of_the_cvd = president_phone_of_the_cvd
                    cvd.treasurer_name_of_the_cvd = treasurer_name_of_the_cvd
                    cvd.treasurer_phone_of_the_cvd = treasurer_phone_of_the_cvd
                    cvd.secretary_name_of_the_cvd = secretary_name_of_the_cvd
                    cvd.secretary_phone_of_the_cvd = secretary_phone_of_the_cvd
                    cvd.save()
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


def get_cvd_under_file_excel_or_csv(file_type, administrative_levels_ids) -> str:

    datas = {
        "REGION" : {}, "PREFECTURE" : {}, "COMMUNE" : {}, "CANTON" : {}, 
        "ID CVD": {}, "CVD": {}, "VILLAGES" : {}, "BANQUE": {}, "CODE BANQUE": {},
        "CODE GUICHET": {}, "N° DE COMPTE": {}, "RIB": {}, 
        "Nom du président du CVD": {}, "Tél du Président du CVD": {}, 
        "Nom du trésorier du CVD": {}, "Tél du trésorier du CVD": {}, 
        "Nom du secrétaire du CVD": {}, "Tél du secrétaire du CVD": {}
    }

    cvds = CVD.objects.filter(
        headquarters_village__id__in=administrative_levels_ids
    ).order_by(
        'headquarters_village__parent__parent__parent__parent__name', 
        'headquarters_village__parent__parent__parent__name', 
        'headquarters_village__parent__parent__name', 
        'headquarters_village__parent__name', 'name'
        )

    count = 0
    for elt in cvds:
        
        try:
            datas["REGION"][count] = elt.headquarters_village.parent.parent.parent.parent.name
        except Exception as exc:
            datas["REGION"][count] = None
        
        try:
            datas["PREFECTURE"][count] = elt.headquarters_village.parent.parent.parent.name
        except Exception as exc:
            datas["PREFECTURE"][count] = None
        
        try:
            datas["COMMUNE"][count] = elt.headquarters_village.parent.parent.name
        except Exception as exc:
            datas["COMMUNE"][count] = None
        
        try:
            datas["CANTON"][count] = elt.headquarters_village.parent.name
        except Exception as exc:
            datas["CANTON"][count] = None
        
        try:
            datas["ID CVD"][count] = elt.id
            datas["CVD"][count] = elt.name
        except Exception as exc:
            datas["ID CVD"][count] = None
            datas["CVD"][count] = elt.name
        
        datas["VILLAGES"][count] = "; ".join([village.name for village in elt.get_villages()])

        datas["BANQUE"][count] = elt.bank
        datas["CODE BANQUE"][count] = elt.bank_code
        datas["CODE GUICHET"][count] = elt.guichet_code
        datas["N° DE COMPTE"][count] = elt.account_number
        datas["RIB"][count] = elt.rib
        datas["Nom du président du CVD"][count] = elt.president_name_of_the_cvd
        datas["Tél du Président du CVD"][count] = elt.president_phone_of_the_cvd
        datas["Nom du trésorier du CVD"][count] = elt.treasurer_name_of_the_cvd
        datas["Tél du trésorier du CVD"][count] = elt.treasurer_phone_of_the_cvd
        datas["Nom du secrétaire du CVD"][count] = elt.secretary_name_of_the_cvd
        datas["Tél du secrétaire du CVD"][count] = elt.secretary_phone_of_the_cvd
        
        count += 1

    if not os.path.exists("media/"+file_type+"/cvds"):
        os.makedirs("media/"+file_type+"/cvds")

    file_name = "cvds_"

    if file_type == "csv":
        file_path = file_type+"/cvds/" + file_name + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") +".csv"
        pd.DataFrame(datas).to_csv("media/"+file_path)
    else:
        file_path = file_type+"/cvds/" + file_name + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") +".xlsx"
        pd.DataFrame(datas).to_excel("media/"+file_path)

    if platform == "win32":
        # windows
        return file_path.replace("/", "\\\\")
    else:
        return file_path