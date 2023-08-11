from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Subproject, VulnerableGroup, SubprojectStep, Level, Step
from administrativelevels.models import AdministrativeLevel, CVD
from subprojects import SUB_PROJECT_SECTORS, TYPES_OF_SUB_PROJECT

class SubprojectForm(forms.ModelForm):
    subproject_sector = forms.ChoiceField(label=_("Subproject sector"), required=True)
    type_of_subproject = forms.ChoiceField(label=_("Type of subproject"), required=True)

    def __init__(self, *args, **kwargs):
        super(SubprojectForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})
            if label in ("list_of_beneficiary_villages", \
                         "list_of_villages_crossed_by_the_track_or_electrification", \
                            "location_subproject_realized"):
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Village")
            
            if label == "canton":
                self.fields[label].queryset = AdministrativeLevel.objects.filter(type="Canton")
                self.fields[label].help_text = _("Fill in this field only if the subproject concerns all the villages in the canton.")
                self.fields[label].label = self.fields[label].label + \
                f" ({_('Fill in this field only if the subproject concerns all the villages in the canton.')})"
            
            if "date" in label:
                self.fields[label].widget.attrs['class'] = 'form-control datetimepicker-input'
            
            choices_datas = {
                'subproject_sector': SUB_PROJECT_SECTORS,
                'type_of_subproject': TYPES_OF_SUB_PROJECT
            }
            instance_datas = {
                'subproject_sector': self.instance.subproject_sector,
                'type_of_subproject': self.instance.type_of_subproject
            }
            if label in ("subproject_sector", "type_of_subproject"):
                self.fields[label].choices = choices_datas[label]
                self.fields[label].widget.choices = choices_datas[label]
                if instance_datas[label]:
                    self.fields[label].initial = instance_datas[label]

    class Meta:
        model = Subproject
        # fields = '__all__' # specify the fields to be displayed
        exclude = ('cvd', )


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
        for label, field in self.fields.items():
            if label in ("begin", "end"):
                self.fields[label].widget.attrs['class'] = 'form-control datetimepicker-input'

            if label == "step":
                self.fields[label].queryset = Step.objects.all().order_by("ranking")

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
        for label, field in self.fields.items():
            if label in ("begin", "end"):
                self.fields[label].widget.attrs['class'] = 'form-control datetimepicker-input'

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