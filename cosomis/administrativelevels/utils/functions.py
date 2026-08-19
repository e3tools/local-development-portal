import pandas as pd
import re
import math
import unicodedata
from fuzzywuzzy import fuzz

def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c))

def normalize_text(text):
    """
    Nettoie et normalise les chaînes de caractères pour améliorer la correspondance.
    """
    if not isinstance(text, str):
        return ""

    text = strip_accents(text)

    text = text.upper().strip()
    
    # 1. Suppression du coût entre parenthèses (si la priorité contient un coût)
    text = re.sub(r'\s*\([^)]+\)', '', text)
    
    # 2. Suppression des verbes d'action/préfixes (essentiel pour les Priorités)
    # Les verbes d'action sont en début de chaîne, mais on les supprime partout pour sécurité.
    actions_a_supprimer = [
        "CONSTRUCTION ", "RÉALISATION ", "RÉHABILITATION ",  "RÉHABILITATION DU ",  "RÉHABILITATION DE ", "EXTENSION ",
        "AMÉNAGEMENT ", "ELECTRIFICATION ", "EXTENTION " # 'extention' est une faute de frappe fréquente
    ]
    for action in actions_a_supprimer:
        # On remplace l'action par un espace (pour éviter de coller deux mots)
        text = text.replace(action, " ")

    # 3. Normalisation des acronymes et variations
    text = text.replace(" EAU DE BOISSON", " AEP")
    text = text.replace(" MARAICHERE", " AGRI")
    text = text.replace(" EP", " EPP")
    text = text.replace(" PRIMAIRE", " EPP")
    text = text.replace(" CMS", " CENTRE MÉDICO-SOCIAL")
    text = text.replace(" USP", " UNITÉ DE SOINS PÉRIPHÉRIQUES")
    text = text.replace(" LYCÉE", " SECOND CYCLE DU SECONDAIRE")
    text = text.replace(" PREMIER CYCLE DU SECONDAIRE", " CEG")
    text = text.replace(" SECONDAIRE (CEG)", " CEG")
    text = text.replace(" JARDIN D'ENFANTS", " PRÉSCOLAIRE")
    text = text.replace(" JEP", " PRÉSCOLAIRE")
    text = text.replace(" PMH", " FORAGES")
    text = text.replace(" AVEC DES LAMPADAIRES SOLAIRES", " HORS RÉSEAU")
    text = text.replace(" de pistes".upper(), " Piste".upper())
    text = text.replace("Electrification avec Panneaux solaires".upper(), "Electrification hors réseau avec des lampadaires solaires".upper())
    
    if "photovoltaïque".upper() in text and "boisson".upper() in text:
        text = "Forages photovoltaïques dans les communautés pour eau de boisson".upper()
    
    if ("jardin".upper() in text and "enfant".upper() in text) or "Pré-scolaire".upper() in text:
        text = "Bâtiments scolaires au préscolaire".upper()
    
    # 4. Nettoyage final
    text = re.sub(r'\s+', ' ', text).strip() # Enlève les espaces multiples

    # Enlever les partir "dans les "
    # text = text.split("DANS LES ")[0]
    text = text.split("DANS ")[0].strip()
    
    return text

def extract_priority_description(text):
    """Extrait la description du projet en retirant le coût (entre parenthèses)."""
    if pd.isna(text):
        return ""
    # Enlève les parenthèses et ce qu'elles contiennent (le coût)
    text = re.sub(r'\s*\([^)]+\)', '', str(text)).strip()
    return text


def safe_value(value):
    try:
        if not value or (value and str(value).lower() in ["nan", "", "none"]):
            return None
        return value
    except:
        return None
    

def safe_float(value):
    try:
        if value in ["NaN", "nan", "", None]:
            return 0
        v = float(value)
        if math.isnan(v):
            return 0
        return v
    except:
        return 0


def _normalize_for_structure_match(text):
    text = strip_accents(text or "").upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)

    text = text.replace("EXTENTION", "EXTENSION")

    return re.sub(r"\s+", " ", text).strip()


def _contains_any(text, *keywords):
    return any(keyword in text for keyword in keywords)


# Règles métier (mots-clés normalisés -> clé de priorité), dans l'ordre de
# priorité : la première dont la condition est vraie l'emporte. Une clé n'est
# retenue que si elle fait partie des `candidate_keys` passées à
# match_structure_to_priority_key (ex. seulement PRIORITE_PURS_C2_TO_CATEGORY).
# Pensées pour être appliquées aux libellés de TYPE_OF_STRUCTURES contre les
# clés de PRIORITE_11_TO_CATEGORY / PRIORITE_13_TO_CATEGORY /
# PRIORITE_PURS_C1_TO_CATEGORY / PRIORITE_PURS_C2_TO_CATEGORY /
# PRIORITE_PURS_C3_TO_CATEGORY (cf. administrativelevels/management/commands/priorities_sync_helpers.py).
STRUCTURE_MATCH_RULES = [
    # Forages / points d'eau : maraîchage-agriculture vs. eau potable (AEP)
    (lambda t: _contains_any(t, "FORAGE") and _contains_any(t, "MARAICH", "AGRI"),
     "Réalisation Forage photovoltaïque Agri"),
    (lambda t: _contains_any(t, "FORAGE"), "Réalisation Forage photovoltaïque AEP"),
    (lambda t: _contains_any(t, "PMH", "POMPE A MOTRICITE"), "Equipement de forage"),

    # Franchissements (avant "retenue d'eau" : un ouvrage de franchissement au
    # niveau d'une retenue d'eau reste une infra de piste, pas un aménagement
    # hydraulique)
    (lambda t: _contains_any(t, "FRANCHISSEMENT"), "Construction Ponceaux"),

    # Eau (hors forage) : retenues/barrages vs. réseau d'adduction
    (lambda t: _contains_any(t, "RETENUE", "BARRAGE"), "Réhabiliter des barrages et retenu d'eau"),
    (lambda t: _contains_any(t, "RESEAU D EAU", "ADDUCTION", "DISTRIBUTION D EAU"),
     "Travaux d'adduction et de distribution d'eau"),

    # Électricité
    (lambda t: _contains_any(t, "RESEAU ELECTRIQUE"), "Extension réseau électrique"),
    (lambda t: _contains_any(t, "ELECTRIFICATION", "LAMPADAIRE", "PANNEAUX SOLAIRE"),
     "Electrification avec Panneaux solaires"),

    # Vocabulaire scolaire spécifique (avant le catch-all scolaire générique)
    (lambda t: _contains_any(t, "CEG"), "Construction Bâtiment scolaire CEG"),
    (lambda t: _contains_any(t, "LYCEE", "SECOND CYCLE"), "Construction Bâtiment scolaire Lycée"),
    (lambda t: _contains_any(t, "ENSEIGNANT"), "Formation des enseignants"),
    (lambda t: _contains_any(t, "ORDINATEUR", "MEDIATHEQUE"), "Acquisition d'ordinateur"),

    # Pistes
    (lambda t: _contains_any(t, "PISTE"), "Amenagement Piste"),

    # Latrines/assainissement (avant le catch-all scolaire et le bloc santé :
    # un bloc de latrines dans une école ou un centre de santé reste une latrine)
    (lambda t: _contains_any(t, "LATRINE") and _contains_any(t, "MARCHE"),
     "Construction de marché y compris les blocs latrines"),
    (lambda t: _contains_any(t, "LATRINE", "DEPOTOIR"), "Construction Latrine communautaire"),

    # Santé : bâtiment (CMS) vs. plateau technique/équipement
    (lambda t: _contains_any(t, "MEDICO SOCIAL", "CMS"), "Construction CMS"),
    # (lambda t: _contains_any(t, "CLOTURE", "PAILLOTE") and _contains_any(t, "SANTE"), "Construction CMS"),
    (lambda t: _contains_any(t, "USP"), "Construction USP"),
    (lambda t: _contains_any(t, "CHP", "HOPITAL", "PEDIATRIE", "MATERNITE", "PERSONNEL DE SANTE"),
     "Réhabilitation CHP"),
    (lambda t: _contains_any(t, "PHARMACIE", "LABORATOIRE", "INCINERATEUR", "OXYGENE", "SANTE"),
     "Equipement CMS"),

    # Marché / commerce / élevage
    (lambda t: _contains_any(t, "ELEVEUR", "BETAIL", "VOLAILLE", "RUMINANT"), "Appui groupements éleveurs"),
    (lambda t: _contains_any(t, "BOUCHERIE", "COMMERCANT"), "Appui commerçants produits Agricoles/élevages"),
    # (lambda t: _contains_any(t, "GARE ROUTIERE"), "Construction d'infrastructures de marché"),
    (lambda t: _contains_any(t, "MARCHE", "BOUTIQUE", "PARKING", "PORTES DE", "HANGAR"),
     "Construction d'infrastructures de marché"),
    (lambda t: _contains_any(t, "MARAICH"), "Appui groupements maraichers"),
    (lambda t: _contains_any(t, "ARTISAN"), "Appui groupements artisans"),

    # Sport
    (lambda t: _contains_any(t, "FOOT", "TERRAIN DE JEUX"), "Aménagement/équipement terrain de foot"),

    # Stockage
    (lambda t: _contains_any(t, "MAGASIN", ), "Construction magasin de stockage"),

    # Environnement
    (lambda t: _contains_any(t, "REBOISEMENT"), "Mise en place de parcs agroforestiers"),

    # Vie communautaire / jeunesse
    (lambda t: _contains_any(t, "MAISON DES JEUNES"), "Construction Maison des jeunes"),
    (lambda t: _contains_any(t, "CENTRE COMMUNAUTAIRE", "SALLE DE REUNION", "SALLE POLYVALENTE", "CENTRE CULTUREL"),
     "Construction Centre communautaire"),

    # Catch-all scolaire (en dernier : le plus générique du lot)
    (lambda t: _contains_any(t, "SCOLAIRE", "ECOLE", "PRESCOLAIRE", "PRE SCOLAIRE", "PRIMAIRE", "EPP"),
     "Construction Bâtiment scolaire EPP"),
]


def match_structure_to_priority_key(structure_name, candidate_keys, threshold=60):
    """Retrouve, parmi `candidate_keys`, la clé de priorité la plus proche de
    `structure_name` (ex. un libellé de TYPE_OF_STRUCTURES).

    `candidate_keys` est typiquement l'union des clés de PRIORITE_11_TO_CATEGORY,
    PRIORITE_13_TO_CATEGORY, PRIORITE_PURS_C1_TO_CATEGORY, PRIORITE_PURS_C2_TO_CATEGORY
    et PRIORITE_PURS_C3_TO_CATEGORY :

        from administrativelevels.management.commands.priorities_sync_helpers import (
            PRIORITE_11_TO_CATEGORY, PRIORITE_13_TO_CATEGORY, PRIORITE_PURS_C1_TO_CATEGORY,
            PRIORITE_PURS_C2_TO_CATEGORY, PRIORITE_PURS_C3_TO_CATEGORY,
        )
        candidate_keys = {
            key
            for d in (PRIORITE_11_TO_CATEGORY, PRIORITE_13_TO_CATEGORY, PRIORITE_PURS_C1_TO_CATEGORY,
                      PRIORITE_PURS_C2_TO_CATEGORY, PRIORITE_PURS_C3_TO_CATEGORY)
            for key in d
        }
        match_structure_to_priority_key('Forage Photovoltaïque (Centre communautaire)', candidate_keys)
        # -> 'Réalisation Forage photovoltaïque AEP'

    Fonctionne en deux temps :
    1) les règles métier de STRUCTURE_MATCH_RULES (mots-clés normalisés -> clé
       cible) sont essayées dans l'ordre, la première qui matche et dont la clé
       fait partie de `candidate_keys` l'emporte ;
    2) à défaut, repli sur un score de similarité (fuzz.token_set_ratio) contre
       chaque clé candidate ; sous `threshold`, retourne 'Autre'.
    """
    candidate_keys = set(candidate_keys)
    text = _normalize_for_structure_match(structure_name)
    if not text:
        return "Autre"

    for condition, key in STRUCTURE_MATCH_RULES:
        if key in candidate_keys and condition(text):
            return key

    best_key, best_score = None, 0
    for key in candidate_keys:
        score = fuzz.token_set_ratio(text, _normalize_for_structure_match(key))
        if score > best_score:
            best_score, best_key = score, key
    return best_key if best_score >= threshold else "Autre"