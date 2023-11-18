from django import forms
from django.forms import RadioSelect, Select

from investments.models import Attachment
from .models import AdministrativeLevel
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.translation import gettext_lazy as _


class AdministrativeLevelForm(forms.ModelForm):
    def __init__(self, parent: str = None, type: str = None, *args, **kwargs):
        super(AdministrativeLevelForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label == "parent":
                print("******* ", parent)
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type=parent)
                self.fields[label].label = parent
            if label == "type":
                self.fields[label].initial = type
                print("######### ", parent)
                
    class Meta:
        model = AdministrativeLevel
        exclude  = ['no_sql_db_id','geographical_unit','cvd','latitude','longitude','frontalier','rural'] # specify the fields to be hid


#SearchVillages
class VillageSearchForm(forms.Form):
    region = forms.ModelChoiceField(queryset=AdministrativeLevel.objects.filter(type="Region"), required=False, empty_label=_("Toutes les régions"))
    prefecture = forms.ModelChoiceField(queryset=AdministrativeLevel.objects.filter(type="Prefecture"), required=False)
    commune = forms.ModelChoiceField(queryset=AdministrativeLevel.objects.filter(type="Commune"), required=False)
    canton = forms.ModelChoiceField(queryset=AdministrativeLevel.objects.filter(type="Canton"), required=False)


class FinancialPartnerForm(forms.Form):
    name = forms.CharField()
    is_full_contribution = forms.BooleanField()
    potential_date = forms.DateField()
    commentaries = forms.CharField(widget=forms.Textarea())


class AttachmentFilterForm(forms.Form):
    TYPE_CHOICES = (
        (Attachment.PHOTO, _('Photo')),
        (Attachment.DOCUMENT, _('Document')),
        (None, _("Both"))
    )
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=RadioSelect)
    phase = forms.ChoiceField(widget=Select, required=False)
    activity = forms.ChoiceField(widget=Select, required=False)
    task = forms.ChoiceField(widget=Select, required=False)
    administrative_level = forms.ChoiceField(widget=Select, required=False)
