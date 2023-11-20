# Generated by Django 4.1.1 on 2023-11-20 12:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AdministrativeLevel",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "frontalier",
                    models.BooleanField(default=True, verbose_name="Frontalier"),
                ),
                ("rural", models.BooleanField(default=True, verbose_name="Rural")),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                        verbose_name="Latitude",
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                        verbose_name="Longitude",
                    ),
                ),
                ("name", models.CharField(max_length=255, verbose_name="Name")),
                ("rank", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status_color",
                    models.CharField(
                        choices=[
                            ("lime_green", "Lime Green"),
                            ("dark_green", "Dark Green"),
                            ("orange", "Orange"),
                            ("red", "Red"),
                        ],
                        default="lime_green",
                        max_length=20,
                    ),
                ),
                (
                    "status_description",
                    models.CharField(
                        choices=[
                            ("early", "Early"),
                            ("normal", "Normal"),
                            ("late", "Late"),
                            ("blocked", "Blocked"),
                        ],
                        default="normal",
                        max_length=15,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("Village", "Village"),
                            ("Canton", "Canton"),
                            ("Commune", "Commune"),
                            ("Region", "Region"),
                            ("Prefecture", "Prefecture"),
                        ],
                        default="Village",
                        max_length=255,
                        verbose_name="Type",
                    ),
                ),
                ("total_population", models.IntegerField(default=0)),
                ("population_men", models.IntegerField(default=0)),
                ("population_women", models.IntegerField(default=0)),
                ("population_young", models.IntegerField(default=0)),
                ("population_elder", models.IntegerField(default=0)),
                ("population_handicap", models.IntegerField(default=0)),
                ("population_agriculturist", models.IntegerField(default=0)),
                ("population_pastoralist", models.IntegerField(default=0)),
                ("population_minorities", models.IntegerField(default=0)),
                (
                    "main_languages",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True)),
                ("updated_date", models.DateTimeField(auto_now=True)),
                (
                    "no_sql_db_id",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_date", models.DateTimeField(auto_now=True, null=True)),
                ("name", models.CharField(max_length=50)),
                ("description", models.CharField(max_length=255)),
                ("implementation_agency", models.CharField(max_length=255)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="GeographicalUnit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_date", models.DateTimeField(auto_now_add=True, null=True)),
                ("updated_date", models.DateTimeField(auto_now=True, null=True)),
                (
                    "attributed_number_in_canton",
                    models.IntegerField(verbose_name="Attributed number in canton"),
                ),
                (
                    "unique_code",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="Unique code"
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, null=True, verbose_name="Description"),
                ),
                (
                    "canton",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="administrativelevels.administrativelevel",
                        verbose_name="Administrative level",
                    ),
                ),
            ],
            options={
                "unique_together": {("canton", "attributed_number_in_canton")},
            },
        ),
        migrations.AddField(
            model_name="administrativelevel",
            name="geographical_unit",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="administrativelevels.geographicalunit",
                verbose_name="Geographical unit",
            ),
        ),
        migrations.AddField(
            model_name="administrativelevel",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="administrativelevels.administrativelevel",
                verbose_name="Parent",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="administrativelevel",
            unique_together={("name", "parent", "type")},
        ),
    ]
