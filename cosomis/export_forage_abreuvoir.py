"""
Export tous les investments du secteur "Accès à l'eau"
dont le type/secteur contient "Forage" ou "abreuvoir".

Run: python manage.py shell < export_forage_abreuvoir.py
Output: forage_abreuvoir_export.csv (à la racine du projet)
"""
import csv
from investments.models import Investment
from administrativelevels.models import Sector

# Trouve le secteur "Forage + abreuvoir"
sectors = Sector.objects.filter(name__icontains="forage")
print(f"Secteurs trouvés : {[(s.id, s.name) for s in sectors]}")

qs = Investment.objects.filter(
    sector__in=sectors
).select_related(
    'sector',
    'sector__category',
    'administrative_level',
    'administrative_level__parent',
    'administrative_level__parent__parent',
    'administrative_level__parent__parent__parent',
    'funded_by',
)

print(f"Total investments trouvés : {qs.count()}")

with open("forage_abreuvoir_export.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "id",
        "titre",
        "sous_composante",
        "secteur",
        "categorie",
        "investment_status",
        "project_status",
        "funded_by",
        "village",
        "arrondissement",
        "commune",
        "departement",
        "cout_estime",
    ])

    for inv in qs:
        adm = inv.administrative_level
        arr = adm.parent if adm else None
        com = arr.parent if arr else None
        dep = com.parent if com else None

        writer.writerow([
            inv.id,
            inv.title or "",
            inv.sub_component or "",
            inv.sector.name if inv.sector else "",
            inv.sector.category.name if inv.sector and inv.sector.category else "",
            inv.investment_status,
            inv.project_status,
            inv.funded_by.name if inv.funded_by else "",
            adm.name if adm else "",
            arr.name if arr else "",
            com.name if com else "",
            dep.name if dep else "",
            inv.estimated_cost or 0,
        ])

print("Export terminé : forage_abreuvoir_export.csv")
