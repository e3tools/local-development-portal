import pandas as pd


def conversion_file_csv_to_dict(file_csv) -> dict:
    read_file = pd.read_csv(file_csv)
    datas = read_file.to_dict()

    return datas

def conversion_file_xlsx_to_dict(file_xlsx) -> dict:
    read_file = pd.read_excel(file_xlsx)
    datas = read_file.to_dict()

    return datas


