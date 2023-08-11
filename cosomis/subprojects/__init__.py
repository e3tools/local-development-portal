from django.utils.translation import gettext_lazy as _

SUB_PROJECT_TYPE_DESIGNATION = (
    ('Subproject', _('Subproject')),
    ('Infrastructure', _('Infrastructure'))
)


SUB_PROJECT_SECTORS = (
    ('', ''),
    ('Developpement–a–la–Base', _('Grassroots-development')), 
    ('Eau–Hydraulique', _('Water-Hydraulics')), 
    ('Pistes', _('Tracks')), 
    ('Education', _('Education')), 
    ('Agriculture', _('Agriculture')), 
    ('Sante', _('Health')), 
    ('Energie', _('Energy')), 
    ('Sport–Loisir', _('Sport-Loisir')), 
    ('Assainissement', _('Sanitation')), 
    ('Environnement', _('Environment'))
)

TYPES_OF_SUB_PROJECT = (
    ('', ''),
    ('Centre Communautaire', _('Community Center')), 
    ('Forage Photovoltaïque (Centre communautaire)', _('Photovoltaic drilling (Community center)')), 
    ('Forage Photovoltaïque (Boisson)', _('Photovoltaic drilling (Beverage)')), 
    ('Piste + OF', _('Track + OF')), 
    ('Batiment Scolaire au CEG', _('School building at CEG')), 
    ('Forage Photovoltaïque (Ecole)', _('Photovoltaic drilling (School)')), 
    ('Magasin De Stockage', _('Storage Warehouse')), 
    ('CMS', _('Medical-social center')), 
    ('Extension réseau électrique', _('Power grid extension')), 
    ("Retenue d'eau", "Water retention"), 
    ('Terrain de Foot', _('Soccer pitch')), 
    ('CHP', _('Prefectural hospital center')), 
    ('Latrine Communautaire', _('Community latrine')), 
    ('Forage Photovoltaïque (Latrines)', _('Photovoltaic drilling (Latrines)')), 
    ('Forage Photovoltaïque (Maraichage)', _('Photovoltaic drilling (market gardening)')), 
    ('USP', _('USP')), ('Batiment Scolaire au Lycée', _('School building at Lycée')), 
    ('Batiment Scolaire au Primaire', _('Primary school building')), 
    ('Pharmacie', _('Pharmacy')), 
    ('Lampadaires solaire', _('Solar street lamps')), 
    ('Pédiatrie', _('Pediatrics')), 
    ('Laboratoire', _('Laboratory')), 
    ('Reboisement', _('Reforestation')), 
    ('Maison des jeunes', _('Youth center')), 
    ('Forage Photovoltaïque (Maison des jeunes)', _('Photovoltaic drilling (youth center)')), 
    ('Salle de réunion', _('Meeting room')), 
    ('Forage Photovoltaïque (Salle de réunion)', _('Photovoltaic drilling (Meeting room)'))
)