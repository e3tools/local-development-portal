import unicodedata
def strip_accents(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(text)) if not unicodedata.combining(c))

PRIORITE_11_TO_CATEGORY = {
    'Construction magasin de stockage': 'Agriculture', 

    'Réhabilitation magasin de stockage': 'Assainissement', 

    'Autre': 'Autre', 

    'Réalisation Forage photovoltaïque Agri': 'Developpement–a–la–Base', 
    'Construction Centre communautaire': 'Developpement–a–la–Base', 
    'Construction Maison des jeunes': 'Developpement–a–la–Base', 

    'Construction Latrine communautaire': 'Eau', 
    'Réalisation Forage photovoltaïque AEP': 'Eau', 

    'Réhabilitation Bâtiment scolaire EPP': 'Education', 
    'Réhabilitation Bâtiment scolaire CEG': 'Education', 
    'Réhabilitation Bâtiment scolaire Lycée': 'Education', 
    'Construction Bâtiment scolaire EPP': 'Education', 
    'Construction Bâtiment scolaire CEG': 'Education', 
    'Construction Bâtiment scolaire Lycée': 'Education', 

    'Extention réseau électrique': 'Energie', 
    'Electrification avec Panneaux solaires': 'Energie', 

    'Construction Ponts': 'Pistes', 
    'Construction Radier': 'Pistes', 
    'Construction Ponceaux': 'Pistes', 
    'Amenagement Piste': 'Pistes', 

    'Réhabilitation CMS': 'Sante', 
    'Réhabilitation CHP': 'Sante', 
    'Construction CMS': 'Sante', 
    'Construction USP': 'Sante', 
    'Réhabilitation USP': 'Sante'
}

PRIORITE_13_TO_CATEGORY = {
    "Réhabilitation/équipement terrain foot": "Sport",
    "Aménagement/équipement terrain de foot": "Sport",
    "Appui groupements maraichers": "Appui Economique",
    "Appui groupements éleveurs": "Appui Economique",
    "Appui groupements producteurs de Maïs": "Appui Economique",
    "Appui groupements producteurs de Riz": "Appui Economique",
    "Appui aux jeunes producteurs de Soja": "Appui Economique",
    "Appui groupements transformateurs": "Appui Economique",
    "Appui groupements artisans": "Appui Economique",
    "Appui commerçants produits Agricoles/élevages": "Appui Economique",
    "Appui Commerçants produits transformés": "Appui Economique",
    "Appui Commerçant produit artisanaux": "Appui Economique",
    "Autre": "Autre",
}

PRIORITE_PURS_C1_TO_CATEGORY = {
    "Renforcement et financement des coopératives de femmes et de jeunes": "Appui Economique",
    "Equipement des jeunes en kits d'outillage": "Appui Economique",

    "Construction Latrine communautaire": "Assainissement",

    "Construction de marché y compris les blocs latrines": "Commerce",

    "Réalisation Forage photovoltaïque AEP": "Eau",
    "Equipement de forage": "Eau",
    "Travaux d'adduction et de distribution d'eau": "Eau",
    "Travaux de renouvellement et d'extension": "Eau",
    "Fourniture et pose de canalisation": "Eau",

    "Construction Bâtiment scolaire EPP": "Education",
    "Construction Bâtiment scolaire CEG": "Education",
    "Construction Bâtiment scolaire Lycée": "Education",
    "Réhabilitation Bâtiment scolaire EPP": "Education",
    "Réhabilitation Bâtiment scolaire CEG": "Education",
    "Réhabilitation Bâtiment scolaire Lycée": "Education",
    "Acquisition de photocopieurs pour écoles": "Education",
    "Acquisition d'ordinateur": "Education",
    "Formation des enseignants": "Education",
    "Fournitures des repas chauds dans les écoles": "Education",
    "Fournitures des repas chauds aux élèves": "Education",
    
    "Construction Maison des jeunes": "Developpement–a–la–Base",
    "Construction Centre communautaire": "Developpement–a–la–Base",
    
    "Electrification avec Panneaux solaires": "Energie",
    "Extension réseau électrique": "Energie",

    "Aménagement Piste": "Pistes",
    "Construction Radier": "Pistes",
    "Construction Ponceaux": "Pistes",
    "Construction Ponts": "Pistes",
    "Construction de dalots multiple": "Pistes",
    "Réhabilitation des plateformes": "Pistes",

    "Construction USP": "Sante",
    "Construction CMS": "Sante",
    "Réhabilitation USP": "Sante",
    "Réhabilitation CMS": "Sante",
    "Réhabilitation CHP": "Sante",
    "Equipement USP": "Sante",
    "Equipement CMS": "Sante",


    "Contrôle et surveillance des travaux": "Autre",
    "Réalisation d'étude technique détaillé": "Autre",
    "Transfère monétaire": "Autre",
    "Extension de la couverture des services voix et internet": "Autre",
    "Autre": "Autre",
}
PRIORITE_PURS_C2_TO_CATEGORY = {
    "Appui groupements maraichers": "Appui Economique",
    "Appui groupements éleveurs": "Appui Economique",
    "Appui groupements producteurs de Maïs": "Appui Economique",
    "Appui groupements producteurs de Riz": "Appui Economique",
    "Appui aux jeunes producteurs de Soja": "Appui Economique",
    "Appui groupements transformateurs": "Appui Economique",
    "Appui groupements artisans": "Appui Economique",
    "Appui commerçants de produits Agricoles/élevages": "Appui Economique",
    "Appui Commerçants de produits transformés": "Appui Economique",
    "Appui Commerçant produit artisanaux": "Appui Economique",
    "Appui aux semences certifiées": "Appui Economique",
    "Appui aux fertilisants et biopesticides": "Appui Economique",
    "Appui aux équipements d'élevage": "Appui Economique",
    "Appui matériel et technique": "Appui Economique",
    
    "Construction d'infrastructures de marché": "Commerce",

    "Réalisation Forage photovoltaïque Agri": "Eau",

    "Construction magasin de stockage": "Agriculture",
    "Aménagement de ZAAP": "Agriculture",
    "Réhabilitation magasin de stockage": "Agriculture",
    "Construction de zones de stockage": "Agriculture",
    "Installation de systèmes d'irrigation": "Agriculture",
    "Aménagement des bas-fonds": "Agriculture",
    "Réhabiliter des barrages et retenu d'eau": "Agriculture",
    "Mise en place de parcs agroforestiers": "Agriculture",
    "Formation en techniques agricoles modernes": "Agriculture",

    "Aménagement des routes pour faciliter l'accès au marché": "Route",

    "Renforcer les capacités des éleveurs": "Renforcement",

    "Réhabilitation/équipement terrain foot": "Sport",
    "Aménagement/équipement terrain de foot": "Sport",

    "Appui à la sensibilisation": "Autre",
    "Autre": "Autre",
}
PRIORITE_PURS_C3_TO_CATEGORY = {
    "Reconnaissance de chef traditionnel": "Gouvernance",
    "Sensibilisation sur la cohésion sociale": "Gouvernance",
    "Formation des magistrats": "Gouvernance",

    "Mise en place d’une maison de justice": "Securite",
    "Construction des commissariats de Police": "Securite",
    "Construction des Brigades de Gendarmerie": "Securite",

    "Autre": "Autre",
}
PRIORITE_13_TO_CATEGORY = {
    "Réhabilitation/équipement terrain foot": "Sport",
    "Aménagement/équipement terrain de foot": "Sport",
    "Appui groupements maraichers": "Appui Economique",
    "Appui groupements éleveurs": "Appui Economique",
    "Appui groupements producteurs de Maïs": "Appui Economique",
    "Appui groupements producteurs de Riz": "Appui Economique",
    "Appui aux jeunes producteurs de Soja": "Appui Economique",
    "Appui groupements transformateurs": "Appui Economique",
    "Appui groupements artisans": "Appui Economique",
    "Appui commerçants produits Agricoles/élevages": "Appui Economique",
    "Appui Commerçants produits transformés": "Appui Economique",
    "Appui Commerçant produit artisanaux": "Appui Economique",
    "Autre": "Autre",
}


# Pour chaque type de structure (TYPE_OF_STRUCTURES), la clé la plus proche parmi
# PRIORITE_11_TO_CATEGORY / PRIORITE_13_TO_CATEGORY / PRIORITE_PURS_C1_TO_CATEGORY /
# PRIORITE_PURS_C2_TO_CATEGORY / PRIORITE_PURS_C3_TO_CATEGORY. Rapprochement fait à
# la main (les deux vocabulaires — nom d'infrastructure vs. libellé d'activité de
# priorité — ne se recouvrent pas assez pour un matching flou fiable)
TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY = {
    'Centre Communautaire': 'Construction Centre communautaire',
    'Forage Photovoltaïque (Centre communautaire)': 'Réalisation Forage photovoltaïque AEP',
    'Forages photovoltaïques dans les communautés pour eau de boisson': 'Réalisation Forage photovoltaïque AEP',
    'Aménagement de pistes': 'Amenagement Piste',
    'Bâtiments scolaires au premier cycle du secondaire (CEG)': 'Construction Bâtiment scolaire CEG',
    'Forages photovoltaïques dans les établissements scolaires': 'Réalisation Forage photovoltaïque AEP',
    'Bâtiments scolaires au primaire': 'Construction Bâtiment scolaire EPP',
    'Magasin de stockage': 'Construction magasin de stockage',
    'Centre Médico-Social (CMS)': 'Construction CMS',
    'Forage Photovoltaïque (Boisson)': 'Réalisation Forage photovoltaïque AEP',
    'Bâtiments scolaires au préscolaire': 'Construction Bâtiment scolaire EPP',
    "Ouvrage de franchissement au niveau de l'établissement scolaire": 'Construction Ponceaux',
    'Extension du réseau électrique': 'Extension réseau électrique',
    "Retenues d'eau": "Réhabiliter des barrages et retenu d'eau",
    'Forage Photovoltaïque (Ecole)': 'Réalisation Forage photovoltaïque AEP',
    'Terrain de Foot': 'Aménagement/équipement terrain de foot',
    'Pistes': 'Amenagement Piste',
    # 'Pédiatrie': 'Réhabilitation CHP',
    # 'Clôtures d’école': 'Construction Bâtiment scolaire EPP',
    'Latrine Communautaire': 'Construction Latrine communautaire',
    'Forages photovoltaïques pour les activités maraîchères': 'Réalisation Forage photovoltaïque Agri',
    # 'Bibliothèques scolaires': 'Construction Bâtiment scolaire EPP',
    "Retenue d'eau": "Réhabiliter des barrages et retenu d'eau",
    # 'Pharmacie': 'Equipement CMS',
    'Electrification hors réseau avec lampadaires solaires': 'Electrification avec Panneaux solaires',
    'Forage Photovoltaïque (Maraichage)': 'Réalisation Forage photovoltaïque Agri',
    'Extension réseau électrique': 'Extension réseau électrique',
    'Electrification hors réseau avec des lampadaires solaires': 'Electrification avec Panneaux solaires',
    'Unité de soins périphériques (USP)': 'Construction USP',
    # 'Laboratoire': 'Equipement CMS',
    # 'Paillote dans les établissements scolaires pour enseignants': 'Formation des enseignants',
    'Bâtiments scolaires au second cycle du secondaire (Lycée)': 'Construction Bâtiment scolaire Lycée',
    'Réhabilitation PMH en Forage Photovoltaïque (Ecole)': 'Réalisation Forage photovoltaïque AEP',
    # 'Reboisement': 'Mise en place de parcs agroforestiers',
    'Maison des jeunes': 'Construction Maison des jeunes',
    'Forage Photovoltaïque (Maison des jeunes)': 'Réalisation Forage photovoltaïque AEP',
    'Ouvrage de franchissement sur la voie publique': 'Construction Ponceaux',
    'Forage Photovoltaïque (Salle de réunion)': 'Réalisation Forage photovoltaïque AEP',
    'Salle de réunion': 'Construction Centre communautaire',
    'Réhabilitation PMH': 'Equipement de forage',
    'Bâtiment Scolaire au Primaire': 'Construction Bâtiment scolaire EPP',
    'PMH à réhabiliter/transformer en Forages photovoltaïques dans les établissements scolaires': 'Réalisation Forage photovoltaïque AEP',
    'Bâtiment Scolaire au CEG': 'Construction Bâtiment scolaire CEG',
    'Bâtiment Scolaire au Pré-scolaire': 'Construction Bâtiment scolaire EPP',
    '': 'Autre',
    # 'Clôture de Centre de santé': 'Construction CMS',
    # "Cantine d'Hôpital": 'Réhabilitation CHP',
    # 'Incinérateurs médicaux': 'Equipement CMS',
    # 'Paillote pour centre de santé': 'Construction CMS',
    "Ouvrage de franchissement au niveau de l'établissment scolaire": 'Construction Ponceaux',
    # 'Blocs de latrines dans les établissements scolaires': 'Construction Latrine communautaire',
    'Vestiaires de Terrain de Foot': 'Aménagement/équipement terrain de foot',
    'Centre artisanal': 'Appui groupements artisans',
    # 'Salle informatique': "Acquisition d'ordinateur",
    'Salle polyvalente': 'Construction Centre communautaire',
    'Ouvrage de franchissement au niveau du Magasin de stockage': 'Construction Ponceaux',
    'Boutiques': "Construction d'infrastructures de marché",
    'Hangar de Gare routière': "Construction d'infrastructures de marché",
    # 'Dortoir': 'Construction Bâtiment scolaire EPP',
    'Hangar de type cantonal': "Construction d'infrastructures de marché",
    'Bloc administratif de marché': "Construction d'infrastructures de marché",
    'Marché à bétail': 'Appui groupements éleveurs',
    'Blocs de latrines dans les marchés': 'Construction Latrine communautaire',
    # 'Dépotoir': 'Construction Latrine communautaire',
    # 'Boucherie': 'Appui commerçants produits Agricoles/élevages',
    'Forages photovoltaïques dans les marchés pour eau de boisson': 'Réalisation Forage photovoltaïque AEP',
    'Clôture/Façade de marché': "Construction d'infrastructures de marché",
    'Parking auto/moto': "Construction d'infrastructures de marché",
    'Ouvrage de franchissement au niveau du marché': 'Construction Ponceaux',
    'Abri pour volailles': 'Appui groupements éleveurs',
    'Abri pour petits ruminants': 'Appui groupements éleveurs',
    'Magasin': 'Construction magasin de stockage',
    'Parking moto': "Construction d'infrastructures de marché",
    'Portes de marché': "Construction d'infrastructures de marché",
    'Abri pour volailles et petits ruminants': 'Appui groupements éleveurs',
    'Réhabilitation du marché moderne de Mango': "Construction d'infrastructures de marché",
    # 'Maternité': 'Réhabilitation CHP',
    # "Local de stockage d'oxygène médical": 'Equipement CMS',
    # 'Clôture de centre communautaire': 'Construction Centre communautaire', # -
    'Centre culturel': 'Construction Centre communautaire',
    "Extension du réseau d'eau (TDE)": "Travaux d'adduction et de distribution d'eau",
    'Ouvrage de franchissement au niveau du centre communautaire': 'Construction Ponceaux',
    "Bloc administratif d'école": 'Construction Bâtiment scolaire EPP',
    'Equipement de centre de santé': 'Equipement CMS',
    # 'Médiathèque': "Acquisition d'ordinateur",
    # 'Logements': 'Construction Bâtiment scolaire EPP',
    'Blocs latrines dans les centres de santé': 'Construction Latrine communautaire',
    'Pompe à motricité humaine (PMH)': 'Equipement de forage',
    'Clôture de terrain de jeux': 'Aménagement/équipement terrain de foot',
    'Tribune de terrain de Foot': 'Aménagement/équipement terrain de foot',
    "Ouvrage de franchissement au niveau de la retenue d'eau": 'Construction Ponceaux',
    'Clôture du site de maraichage': 'Appui groupements maraichers',
    # 'Latrines dans les terrains de football': 'Aménagement/équipement terrain de foot', # -
    # 'Logements du personnel de santé': 'Réhabilitation CHP',
}
TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY_IGNORE_ACCENTS = {strip_accents(k): v for k, v in TYPE_OF_STRUCTURES_TO_PRIORITY_CATEGORY.items()}