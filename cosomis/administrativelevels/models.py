from email.policy import default
from django.db import models

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

    def __str__(self):
        return self.name


class Village(models.Model):
    """Model to present the village"""
    name = models.CharField(max_length=150)
    administrative_level = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

