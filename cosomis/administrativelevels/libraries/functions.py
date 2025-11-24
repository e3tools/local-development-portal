import unicodedata
import re
from datetime import datetime
from dateutil import parser

def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')


import re
from datetime import datetime
from dateutil import parser

MONTHS_FR = {
    "janvier": "01", "février": "02", "fevrier": "02", "mars": "03",
    "avril": "04", "mai": "05", "juin": "06",
    "juillet": "07", "aout": "08", "août": "08",
    "septembre": "09", "octobre": "10",
    "novembre": "11", "decembre": "12", "décembre": "12"
}

def clean_date(raw):
    if not raw or not isinstance(raw, str):
        return None

    s = raw.lower().strip()
    s = s.replace("_", "/")
    s = s.replace("–", "-")
    s = re.sub(r"\s+", " ", s)  # normalisation espaces

    # -----------------------------
    # Extraire la dernière date après "et" ou "au"
    # -----------------------------
    if " et " in s:
        s = s.split(" et ")[-1].strip()

    if " au " in s:
        s = s.split(" au ")[-1].strip()

    # -----------------------------
    # Format type 09-10/12/2022 -> prendre 10/12/2022
    # -----------------------------
    if re.search(r"\d{1,2}-\d{1,2}/\d{1,2}/\d{4}", s):
        first, month, year = re.split(r"/", s)
        day = first.split("-")[-1]
        s = f"{day}/{month}/{year}"

    # -----------------------------
    # Corriger formats collés ex : 05-052023 -> 05/05/2023
    # -----------------------------
    # cas "-" séparateur
    m = re.match(r"^(\d{1,2})-(\d{2})(\d{4})$", s)
    if m:
        day, month, year = m.groups()
        s = f"{day}/{month}/{year}"

    # cas "/" séparateur (ex: 18/112023)
    m = re.match(r"^(\d{1,2})/(\d{2})(\d{4})$", s)
    if m:
        day, month, year = m.groups()
        s = f"{day}/{month}/{year}"

    # -----------------------------
    # Corriger dates éclatées → ex : 09/10/12/20/2022
    # -----------------------------
    parts = re.findall(r"\d{1,4}", s)
    if len(parts) >= 3:
        day = parts[-3]
        month = parts[-2]
        year = parts[-1]

        # Corriger année courte
        if len(year) == 2:
            year = "20" + year

        # Vérification de validité basique
        if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
            s = f"{day}/{month}/{year}"

    # -----------------------------
    # Gestion des dates textuelles "21 novembre 2022"
    # -----------------------------
    for name, month in MONTHS_FR.items():
        if name in s:
            s = s.replace(name, month)
            # s devient "21 11 2022"
            s = re.sub(r"(\d{1,2})\s+(\d{2})\s+(\d{4})", r"\1/\2/\3", s)
            break

    # Supprimer espaces parasites "21/11/ 2022"
    s = re.sub(r"/\s+", "/", s)

    return s


def safe_parse_date(raw):
    cleaned = clean_date(raw)
    if not cleaned:
        return None

    formats = [
        "%d/%m/%Y", "%Y/%m/%d",
        "%d-%m-%Y", "%Y-%m-%d",
        "%d/%m/%y", "%d-%m-%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except:
            pass

    return parser.parse(cleaned, dayfirst=True)
