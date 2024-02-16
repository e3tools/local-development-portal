from django import forms
from .models import Package, Investment


class InvestmentsForm(forms.Form):
    investments = forms.CharField()

    def __init__(self, *args, context=None, **kwargs):
        self.context = context
        super().__init__(*args, **kwargs)

    def clean_investments(self):
        if not hasattr(self, 'context'):
            raise 'Need context.'
        if 'user' not in self.context:
            raise 'Need user.'
        data = self.cleaned_data['investments']
        investment_ids = self.cleaned_data['investments'].split(',')
        investment_ids.remove('')
        investments = Investment.objects.filter(id__in=investment_ids)
        package = Package.objects.get_active_cart(
            user=self.context['user']
        )
        for inv in investments:
            package.funded_investments.add(inv)
        return data


class PackageApprovalForm(forms.Form):
    package = forms.ModelChoiceField(queryset=Package.objects.filter(status=Package.PENDING_APPROVAL))
    approve = forms.BooleanField()
    no_resubmission = forms.BooleanField(widget=forms.CheckboxInput())
    reject_reason = forms.CharField(widget=forms.Textarea())
