from django.db import migrations

SOURCE = "realisation_images"

# Aliases discovered while processing the realisation images folder.
# All map folder name spellings to the correct DB name.
SIMPLE_ALIASES = {
    "village": {
        "GNÉMASSON":       ["Gnemasson"],
        "BOUMOUSSOU":      ["Bomoussou"],
        "BOFOUNOU":        ["Founougo-Peulh", "FOUNOUGO-PEULH"],
        "DÈGUÈ-DÈGUÉ":    ["Dèguè-Dèguè", "DÈGUÈ-DÈGUÈ"],
        "BAKO-MAKA":       ["Bako Maka", "BAKO MAKA"],
        "MACHAYAN-MARCHÉ": ["Machayan_marché", "MACHAYAN_MARCHÉ"],
        "DANGANZI":        ["Dangazi", "DANGAZI"],
    },
    "arrondissement": {
        "TOUMBOUTOU": ["Tomboutou", "TOMBOUTOU"],
    },
}


def populate_aliases(apps, schema_editor):
    AdministrativeLevel = apps.get_model("administrativelevels", "AdministrativeLevel")
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")

    created = 0
    skipped = 0
    errors = []

    for adm_type, entries in SIMPLE_ALIASES.items():
        for db_name, alias_list in entries.items():
            qs = AdministrativeLevel.objects.filter(
                name__iexact=db_name,
                type__iexact=adm_type,
            )
            if not qs.exists():
                errors.append(f"NOT FOUND [{adm_type}] '{db_name}'")
                continue
            if qs.count() > 1:
                errors.append(
                    f"AMBIGUOUS [{adm_type}] '{db_name}' ({qs.count()} results)"
                )
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
        f"\n[0031_realisation_image_aliases] "
        f"created={created}, skipped={skipped}, errors={len(errors)}"
    )
    for e in errors:
        print(f"  ⚠️  {e}")


def depopulate_aliases(apps, schema_editor):
    AdministrativeLevelAlias = apps.get_model("administrativelevels", "AdministrativeLevelAlias")
    AdministrativeLevelAlias.objects.filter(source=SOURCE).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("administrativelevels", "0030_populate_adm_level_aliases"),
    ]

    operations = [
        migrations.RunPython(populate_aliases, reverse_code=depopulate_aliases),
    ]
