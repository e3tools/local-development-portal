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
    administrative_level = models.ForeignKey(AdministrativeLevel, null=False, on_delete=models.CASCADE)

    def __str__(self):
        return self.name




class BaseModel(models.Model):
	created_date = models.DateTimeField(auto_now_add = True, blank=True, null=True)
	updated_date = models.DateTimeField(auto_now = True, blank=True, null=True)

	class Meta:
		abstract = True


class VillageObstacle(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    focus_group = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.description


class VillageGoal(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    focus_group = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.description


class VillagePriority(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    subcomponent = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    proposed_men = models.IntegerField(null=True)
    proposed_women = models.IntegerField(null=True)
    estimated_cost = models.FloatField(null=True)
    estimated_beneficiaries = models.IntegerField(null=True)
    climate_changing_contribution = models.TextField(null=True)
    eligibility = models.BooleanField(blank=True, null=True)
    sector = models.CharField(max_length=255, null=True)
    parent = models.ForeignKey('VillagePriority', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class TypeMain(BaseModel):
    administrative_level = models.ForeignKey(VillagePriority, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    def __str__(self):
        return "{} : {}".format(self.name, self.value)



class PrioritiesMeeting(BaseModel):
    description = models.TextField()
    date_conducted = models.DateTimeField()
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    village_obstacle = models.ForeignKey(VillageObstacle, null=True, blank=True, on_delete=models.CASCADE)
    village_goal = models.ForeignKey(VillageGoal, null=True, blank=True, on_delete=models.CASCADE)
    village_priority = models.ForeignKey(VillagePriority, null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.description

