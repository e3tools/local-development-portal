from django import forms
from django.utils.translation import gettext_lazy as _


#UploadFileForm
class UploadFileForm(forms.Form):
    url = forms.FileField(label=_('Please select the file'), required=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
#End UploadFileForm