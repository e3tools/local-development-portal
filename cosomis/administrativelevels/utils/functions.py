import pandas as pd
import re

def normalize_text(text):
    """
    Nettoie et normalise les chaînes de caractères pour améliorer la correspondance.
    """
    if not isinstance(text, str):
        return ""
    
    text = text.upper().strip()
    
    # 1. Suppression du coût entre parenthèses (si la priorité contient un coût)
    text = re.sub(r'\s*\([^)]+\)', '', text)
    
    # 2. Suppression des verbes d'action/préfixes (essentiel pour les Priorités)
    # Les verbes d'action sont en début de chaîne, mais on les supprime partout pour sécurité.
    actions_a_supprimer = [
        "CONSTRUCTION ", "RÉALISATION ", "RÉHABILITATION ", "EXTENSION ",
        "AMÉNAGEMENT ", "ELECTRIFICATION ", "EXTENTION " # 'extention' est une faute de frappe fréquente
    ]
    for action in actions_a_supprimer:
        # On remplace l'action par un espace (pour éviter de coller deux mots)
        text = text.replace(action, " ")

    # 3. Normalisation des acronymes et variations
    text = text.replace(" AEP", " EAU DE BOISSON")
    text = text.replace(" AGRI", " MARAICHERE")
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
    text = text.split("DANS LES ")[0]
    
    return text

def extract_priority_description(text):
    """Extrait la description du projet en retirant le coût (entre parenthèses)."""
    if pd.isna(text):
        return ""
    # Enlève les parenthèses et ce qu'elles contiennent (le coût)
    text = re.sub(r'\s*\([^)]+\)', '', str(text)).strip()
    return text