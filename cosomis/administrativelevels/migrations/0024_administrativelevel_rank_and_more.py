# Generated by Django 4.1.1 on 2023-11-02 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administrativelevels', '0023_remove_investment_administrative_level_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='administrativelevel',
            name='rank',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='administrativelevel',
            name='type',
            field=models.CharField(choices=[('village', 'Village'), ('canton', 'Canton'), ('commune', 'Commune'), ('region', 'Region'), ('prefecture', 'Prefecture')], default='village', max_length=255, verbose_name='Type'),
        ),
    ]
