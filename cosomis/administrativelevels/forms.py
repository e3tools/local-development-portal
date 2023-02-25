from django import forms
from .models import GeographicalUnit, CVD, AdministrativeLevel
from django.core.exceptions import NON_FIELD_ERRORS

class GeographicalUnitForm(forms.ModelForm):
    
    # cvds = forms.MultipleChoiceField(required=False, label="CVD")
    villages = forms.MultipleChoiceField(required=False, label="Villages")
    def __init__(self, *args, **kwargs):
        super(GeographicalUnitForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label == "canton":
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Canton")
        self.fields['villages'].choices = [(o.id, o.name) for o in AdministrativeLevel.objects.filter(type="Village") if o.parent]
        # d = {}

        # _cvds = CVD.objects.filter()
        # d['cvds'] = list(set([(obj.pk, obj.get_name()) for obj in _cvds if obj.administrativelevel_set.get_queryset()]))

        # for field_name, values in d.items():
        #     # self.fields[field_name].queryset = values
        #     self.fields[field_name].widget.choices = values
        #     self.fields[field_name].choices = values
        #     self.fields[field_name].widget.attrs['class'] += ' ' + field_name

    class Meta:
        model = GeographicalUnit
        exclude  = ['unique_code'] # specify the fields to be hid
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Le numéro d'unité géographique doit être unique dans un canton.",
            }
        }

    

class CVDForm(forms.ModelForm):
    villages = forms.MultipleChoiceField(required=False, label="Villages")
    def __init__(self, *args, **kwargs):
        super(CVDForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
        self.fields['villages'].choices = [(o.id, o.name) for o in AdministrativeLevel.objects.filter(type="Village") if o.parent]

    class Meta:
        model = CVD
        exclude  = ['unique_code'] # specify the fields to be hid

    def clean(self):
        villages = self.cleaned_data['villages']
        if not villages:
            raise forms.ValidationError("Au moins un village doit être sélectionné.")
        return super().clean()
    


class AdministrativeLevelForm(forms.ModelForm):
    def __init__(self, parent: str = None, *args, **kwargs):
        super(AdministrativeLevelForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label == "parent":
                print(parent)
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type=parent)
                self.fields[label].label = parent

    class Meta:
        model = AdministrativeLevel
        exclude  = ['no_sql_db_id'] # specify the fields to be hid
