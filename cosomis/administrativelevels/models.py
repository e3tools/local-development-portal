from email.policy import default
from django.db import models
from cdd_client import CddClient
from django.db.models.signals import post_save


# Create your models here.
class AdministrativeLevel(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    frontalier = models.BooleanField(default=True)
    rural = models.BooleanField(default=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)

    def __str__(self):
        return self.name

    def get_list_priorities(self):
        """Method to get the list of the all priorities that the administrative is linked"""
        return self.villagepriority_set.get_queryset()
    
    def get_list_subprojects(self):
        """Method to get the list of the all subprojects that the administrative is linked"""
        return self.subproject_set.get_queryset()


def update_or_create_amd_couch(sender, instance, **kwargs):
    print("test", instance.id, kwargs['created'])
    client = CddClient()
    if kwargs['created']:
        couch_object_id = client.create_administrative_level(instance)
        to_update = AdministrativeLevel.objects.filter(id=instance.id)
        to_update.update(no_sql_db_id=couch_object_id)
    else:
        client.update_administrative_level(instance)



post_save.connect(update_or_create_amd_couch, sender=AdministrativeLevel)
