from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Subproject, VulnerableGroup, SubprojectStep, Level
from administrativelevels.models import AdministrativeLevel, CVD

class SubprojectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SubprojectForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            # if label == "administrative_level":
            #     self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Village")
            #     self.fields[label].label = "Village"
            #(type__in=['Village','Canton'])
            if label == "cvds":
                self.fields[label].queryset = CVD.objects.filter()
                self.fields[label].label = "CVD"
            
            if "date" in label:
                self.fields[label].widget.attrs['class'] = 'form-control datetimepicker-input'

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

#Add
class SubprojectAddStepForm(forms.ModelForm):
    begin = forms.DateField(label=_('Begin'), input_formats=['%d/%m/%Y'],
                                      help_text="DD/MM/YYYY")
    end = forms.DateField(label=_('End'), input_formats=['%d/%m/%Y'],
                                      help_text="DD/MM/YYYY", required=False)
    def __init__(self, *args, **kwargs):
        # initial = kwargs.get('initial')
        # doc_id = initial.get('doc_id')
        super().__init__(*args, **kwargs)

    class Meta:
        model = SubprojectStep
        fields = (
            'step', 'begin', 'end', 'description', 
            'amount_spent_at_this_step', 'total_amount_spent'
        ) # specify the fields to be displayed


class SubprojectAddLevelForm(forms.ModelForm):
    begin = forms.DateField(label=_('Begin'), input_formats=['%d/%m/%Y'],
                                      help_text="DD/MM/YYYY")
    end = forms.DateField(label=_('End'), input_formats=['%d/%m/%Y'],
                                      help_text="DD/MM/YYYY", required=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Level
        fields = (
            'wording', 'percent', 'ranking', 'begin', 'end', 'description', 
            'amount_spent_at_this_step', 'total_amount_spent'
        ) # specify the fields to be displayed
#And Add



# #Delete
# class DeleteConfirmForm(forms.Form):
#     confirmation = forms.BooleanField(label=_('Please check this box and click the confirmation button for validation.'),
#                                        widget=forms.CheckboxInput, required=True)
    
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
# #And Delete