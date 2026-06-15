# Maps known sector name variants (e.g. mixed apostrophe types) to their
# canonical form as stored in the database.
#
# Use case: when a sector lookup fails, try resolving it through this dict
# before giving up. Add new entries here as mismatches are discovered.
#
# Format:
#   "variant name as it appears in the source data": "canonical name in DB"

SECTOR_ALIASES: dict[str, str] = {
    "Gare routière à l'intérieur ou à proximité du marché": "Gare routière à l’intérieur ou à proximité du marché",
    "Lits de maternité et d'hospitalisation": "Lits de maternité et d’hospitalisation",
    "Bureau d'école primaire" : "Bureau d’école primaire",
    "Centre de santé d’arrondissement (CSA) ou Centre de santé de commune (CSC)" : "Centre de santé d'arrondissement (CSA) ou Centre de santé de commune (CSC)",
    "Infrastructure d’alphabétisation" : "Infrastructure d'alphabétisation",
    "Poste d’eau autonome (PEA)" : "Poste d'eau autonome (PEA)",
    "Infrastructures d’éclairage scolaires + équipements" : "Infrastructures d'éclairage scolaires + équipements",
    "Adduction d’eau villageoise (AEV)" : "Adduction d'eau villageoise (AEV)",
    "Passage d’accès à l’intérieur d’un marché" : "Passage d'accès à l'intérieur d'un marché",
    "Mobilier/équipement d’alpahébisation" : "Mobilier/équipement d'alpahébisation",
}
