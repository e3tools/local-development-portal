# Generated by Django 4.1.1 on 2023-11-05 10:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("investments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="investment",
            name="no_sql_id",
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="investment",
            name="ranking",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
