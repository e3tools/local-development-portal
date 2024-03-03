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
            self.fields[label].widget.attrs.update({"class": "form-control"})
            if label == "parent":
                print("******* ", parent)
                self.fields[label].queryset = AdministrativeLevel.objects.filter(
                    type=parent
                )
                self.fields[label].label = parent
            if label == "type":
                self.fields[label].initial = type
                print("######### ", parent)

    class Meta:
        model = AdministrativeLevel
        exclude = [
            "no_sql_db_id",
            "geographical_unit",
            "cvd",
            "latitude",
            "longitude",
            "frontalier",
            "rural",
        ]  # specify the fields to be hid


# SearchVillages
class VillageSearchForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Region"),
        required=False,
        empty_label=_("Toutes les régions"),
        label=_("Region"),
    )
    prefecture = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Prefecture"),
        required=False,
        label=_("Prefecture"),
    )
    commune = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Commune"),
        required=False,
        label=_("Commune"),
    )
    canton = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Canton"),
        required=False,
        label=_("Canton"),
    )


class FinancialPartnerForm(forms.Form):
    name = forms.CharField()
    is_full_contribution = forms.BooleanField()
    potential_date = forms.DateField()
    commentaries = forms.CharField(widget=forms.Textarea())


class AttachmentFilterForm(forms.Form):
    TYPE_CHOICES = (
        (Attachment.PHOTO, _("Photo")),
        (Attachment.DOCUMENT, _("Document")),
        (None, _("Both")),
    )
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=RadioSelect, label=_("Type"))
    phase = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Phase"))
    activity = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Activity"))
    task = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Task"))
    administrative_level = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type=AdministrativeLevel.VILLAGE),
        widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Administrative level")
    )
