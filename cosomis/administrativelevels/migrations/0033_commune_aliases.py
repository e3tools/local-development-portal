from django.db import migrations

SOURCE = "coso_complet_import_33"

# ---------------------------------------------------------------------------
# Commune aliases missing from previous migrations.
# These cause resolve_adm_level to fail when the import uses accented commune
# names that differ from the DB spelling.
# ---------------------------------------------------------------------------
COMMUNE_ALIASES = {
    # DB has 'BEMBEREKE' (no accents), import uses 'BEMBÈRÈKÈ'
    "BEMBEREKE": ["BEMBÈRÈKÈ", "Bembèrèkè", "BEMBÈRÈKE"],
    # DB has N\u2019DALI (typographic apostrophe), import uses N'DALI (straight)
    "N\u2019DALI": ["N'DALI", "N'dali"],
}


def populate_aliases(apps, schema_editor):
    AdministrativeLevel = apps.get_model("administrativelevels", "AdministrativeLevel")
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")

    created = 0
    skipped = 0
    errors  = []

    for db_name, alias_list in COMMUNE_ALIASES.items():
        qs = AdministrativeLevel.objects.filter(
            name__iexact=db_name,
            type__iexact="commune",
        )
        if not qs.exists():
            errors.append(f"NOT FOUND [commune] '{db_name}'")
            continue
        if qs.count() > 1:
            errors.append(f"AMBIGUOUS [commune] '{db_name}' ({qs.count()} results)")
            continue
        adm = qs.first()
        for alias in alias_list:
            _, was_created = AdministrativeLevelAlias.objects.get_or_create(
                administrative_level=adm,
                name=alias,
                defaults={"source": SOURCE},
            )
            created += was_created
            skipped += not was_created

    print(
        f"\n[0033_commune_aliases] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0032_coso_complet_aliases"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]
