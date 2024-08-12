# Generated by Django 4.1.1 on 2024-08-12 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0010_remove_sector_category_alter_investment_sector_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='investment',
            name='latitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Latitude'),
        ),
        migrations.AddField(
            model_name='investment',
            name='longitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Longitude'),
        ),
        migrations.AlterField(
            model_name='investment',
            name='project_status',
            field=models.CharField(choices=[('N', 'Not Funded'), ('F', 'Funded'), ('P', 'In Progress'), ('C', 'Completed')], default='N', max_length=30),
        ),
    ]
