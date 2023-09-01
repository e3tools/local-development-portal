from django.db import models
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel
from subprojects.models import Project
from authentication.models import Facilitator
from cosomis.models_base import BaseModel

class AssignAdministrativeLevelToFacilitator(BaseModel):
    administrative_level = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE)
    facilitator_id = models.CharField(max_length=255)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    activated = models.BooleanField(default=True)
    assign_date = models.DateField(null=True, blank=True)
    unassign_date = models.DateField(null=True, blank=True)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['administrative_level', 'project'], 
                condition=models.Q(activated=True), 
                name='unique_administrative_level_project_activated') #constraint defining that an assignment is only necessary in a village at a given time
        ]

    @property
    def facilitator(self):
        try:
            return Facilitator.objects.using('cdd').get(id=int(self.facilitator_id))
        except Facilitator.DoesNotExist as e:
            return None
        except:
            return None

    def __str__(self):
        return f'{self.facilitator.name} {_("at")} {self.administrative_level.name}'