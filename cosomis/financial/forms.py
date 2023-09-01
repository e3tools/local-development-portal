from django import forms
from django.utils.translation import gettext_lazy as _

from .models.allocation import AdministrativeLevelAllocation
from administrativelevels.models import AdministrativeLevel


class AdministrativeLevelAllocationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AdministrativeLevelAllocationForm, self).__init__(*args, **kwargs)
        
        self.fields['administrative_level'].choices = [
            (o.id, f'{o.name} ({o.type} {_("Of")} {o.parent if o.parent else "TOGO" })') for o in AdministrativeLevel.objects.filter().order_by('name')
        ]

    class Meta:
        model = AdministrativeLevelAllocation
        fields = '__all__'
