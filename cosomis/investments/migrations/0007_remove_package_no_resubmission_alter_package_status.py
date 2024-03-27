# Generated by Django 4.1.1 on 2024-03-12 11:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investments', '0006_attachment_task'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='package',
            name='no_resubmission',
        ),
        migrations.AlterField(
            model_name='package',
            name='status',
            field=models.CharField(choices=[('PS', 'Pending Submission'), ('P', 'Pending Approval'), ('A', 'Approved'), ('R', 'Rejected'), ('C', 'Closed'), ('E', 'Under Execution')], default='PS', max_length=50),
        ),
    ]
