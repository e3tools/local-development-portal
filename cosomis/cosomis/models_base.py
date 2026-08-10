from django.db import models
import json


# Create your models here.
class BaseModel(models.Model):
    created_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_date = models.DateTimeField(auto_now=True, blank=True, null=True)

    class Meta:
        abstract = True
    
    def save_and_return_object(self):
        super().save()
        return self



def safe_json_value(value, max_depth=3):
    """Retourne la vraie valeur (dict/list/...) d'un `JSONField` même quand elle a été stockée
    double-encodée. Décode tant que la valeur reste une chaîne, avec une limite de
    profondeur pour ne jamais boucler sur une chaîne qui ressemble à du JSON par coïncidence."""
    for _ in range(max_depth):
        if not isinstance(value, str):
            break
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            break
    return value