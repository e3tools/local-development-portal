from django.db import models
from administrativelevels.models import AdministrativeLevel


# Create your models here.
class Subproject(models.Model):
    short_name = models.CharField(max_length=255)
    description = models.TextField()
    administrative_level = models.ForeignKey(AdministrativeLevel, null=False, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    target_female_beneficiaries = models.IntegerField()
    target_male_beneficiaries = models.IntegerField()
    target_youth_beneficiaries = models.IntegerField()
    component = models.CharField(max_length=255)
    sub_component = models.CharField(max_length=255)
    priorities = models.ManyToManyField('CommunityPriority', null=True, blank=True)

    def __str__(self):
        return self.short_name


class CommunityPriority(models.Model):
    administrative_level = models.ForeignKey(AdministrativeLevel, null=False, on_delete=models.CASCADE)
    description = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description


class VulnerableGroup(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
