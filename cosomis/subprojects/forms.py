from django import forms
from .models import Subproject

class SubprojectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(SubprojectForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({'class' : 'form-control'})


    class Meta:
        model = Subproject
        fields = '__all__' # specify the fields to be displayed
