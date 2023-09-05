from django.db import models
from django.apps import apps

from cosomis.models_base import BaseModel



class CustomerFile(BaseModel):
    class_name = models.CharField(max_length=50)
    object_id = models.IntegerField()
    url = models.CharField(max_length=255)
    name = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(default=0)
    principal = models.BooleanField(default=False)
    date_taken = models.DateField(blank=True, null=True)


    def object(self):
        try:
            ClassModal = None
            for app_conf in apps.get_app_configs():
                try:
                    ClassModal = app_conf.get_model(self.class_name.lower())
                    break # stop as soon as it is found
                except LookupError:
                    # no such model in this application
                    pass
            
            if ClassModal:
                return ClassModal.objects.get(id=self.object_id)
        except:
            pass

        return None