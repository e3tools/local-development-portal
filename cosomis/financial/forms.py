from django import forms
from django.utils.translation import gettext_lazy as _

from .models.allocation import AdministrativeLevelAllocation
from administrativelevels.models import AdministrativeLevel, CVD
from financial.models.financial import BankTransfer, DisbursementRequest, Disbursement


class AdministrativeLevelAllocationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(AdministrativeLevelAllocationForm, self).__init__(*args, **kwargs)
        
        self.fields['administrative_level'].choices = [('', '---------')] + [
            (o.id, f'{o.name} ({o.type} {_("Of")} {o.parent if o.parent else "TOGO" })') for o in AdministrativeLevel.objects.filter().order_by('name')
        ]

        self.fields['cvd'].choices = [('', '---------')] + [
            (o.id, f'{o.name} ({o.headquarters_village.parent.name})') for o in CVD.objects.filter().order_by('name')
        ]

    class Meta:
        model = AdministrativeLevelAllocation
        fields = '__all__'


    def clean(self):
        administrative_level = self.cleaned_data['administrative_level']
        cvd = self.cleaned_data['cvd']
        if cvd and administrative_level:
            raise forms.ValidationError(_("You must select either an administrative level or a CVD"))
        elif not cvd and not administrative_level:
            raise forms.ValidationError(_("You must choose an administrative level or a CVD"))
        return super().clean()


class BankTransferForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(BankTransferForm, self).__init__(*args, **kwargs)

        self.fields['administrative_level'].choices = [('', '---------')] + [
            (o.id, f'{o.name} ({o.type} {_("Of")} {o.parent if o.parent else "TOGO" })') for o in AdministrativeLevel.objects.filter().order_by('name')
        ]

        self.fields['cvd'].choices = [('', '---------')] + [
            (o.id, f'{o.name} ({o.headquarters_village.parent.name})') for o in CVD.objects.filter().order_by('name')
        ]

    class Meta:
        model = BankTransfer
        fields = '__all__'
        
    def clean(self):
        administrative_level = self.cleaned_data['administrative_level']
        cvd = self.cleaned_data['cvd']
        if cvd and administrative_level:
            raise forms.ValidationError(_("You must select either an administrative level or a CVD"))
        elif not cvd and not administrative_level:
            raise forms.ValidationError(_("You must choose an administrative level or a CVD"))
        return super().clean()
    

class DisbursementRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DisbursementRequestForm, self).__init__(*args, **kwargs)

    class Meta:
        model = DisbursementRequest
        fields = '__all__'



class DisbursementForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(DisbursementForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Disbursement
        fields = '__all__'

        