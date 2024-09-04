from django import forms
from django.utils.translation import gettext_lazy as _
from usermanager.models import User
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
        investments = Investment.objects.filter(
            id__in=investment_ids,
            project_status=Investment.NOT_FUNDED
        )
        package = Package.objects.get_active_cart(
            user=self.context['user']
        )
        for inv in investments:
            package.funded_investments.add(inv)
        return data


class PackageApprovalForm(forms.Form):
    package = forms.ModelChoiceField(queryset=Package.objects.filter(status=Package.PENDING_APPROVAL))
    no_resubmission = forms.BooleanField(widget=forms.CheckboxInput(), required=False)
    reject_reason = forms.CharField(widget=forms.Textarea(attrs={'required': 'true'}),
                                    required=False,
                                    label=_('Reject reason'),
                                    help_text=_('You are about to send this submission for '
                                                'revision. The submitter will see flagged '
                                                'investments. Please leave comments to help '
                                                'with re-submission.'))

    def save(self):
        package = self.cleaned_data['package']
        if 'reject_reason' in self.cleaned_data and self.cleaned_data['reject_reason'] not in [None, '']:
            package.rejection_reason = self.cleaned_data['reject_reason']
            package.status = Package.REJECTED
            if 'no_resubmission' in self.cleaned_data and self.cleaned_data['no_resubmission']:
                package.status = Package.CLOSED
        else:
            package.status = Package.APPROVED
        package.save()


class UserApprovalForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.all())
    action = forms.CharField()
    success_message = ''

    def save(self):
        if self.cleaned_data['action'] == 'approve':
            self.cleaned_data['user'].is_approved = True
            self.cleaned_data['user'].is_active = True
            self.success_message = 'User approve successfully.'
        elif self.cleaned_data['action'] == 'reject':
            self.cleaned_data['user'].is_approved = False
            self.cleaned_data['user'].is_active = False
            self.success_message = 'User reject successfully.'
        elif self.cleaned_data['action'] == 'spam':
            pass

        self.cleaned_data['user'].save()
