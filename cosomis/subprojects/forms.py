from django import forms
from .models import Subproject, VulnerableGroup
from administrativelevels.models import AdministrativeLevel

class SubprojectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SubprojectForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label == "administrative_level":
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Village")
                self.fields[label].label = "Village"


    class Meta:
        model = Subproject
        fields = '__all__' # specify the fields to be displayed


class VulnerableGroupForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(VulnerableGroupForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label == "administrative_level":
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Village")
                self.fields[label].label = "Village"


    class Meta:
        model = VulnerableGroup
        fields = '__all__' # specify the fields to be displayed
