from django import forms
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import Project
from usermanager.models import User
from .models import Package, Investment


class InvestmentsForm(forms.Form):
    investments = forms.CharField(required=False)
    all_queryset = forms.CharField()
    project = forms.ModelChoiceField(queryset=Project.objects.all())

    def __init__(self, *args, context=None, **kwargs):
        self.context = context
        if not hasattr(self, 'context'):
            raise 'Need context.'
        if 'user' not in self.context:
            raise 'Need user.'
        super().__init__(*args, **kwargs)
        self.fields['project'].queryset = Project.objects.filter(organization=context["user"].organization)
        self.package = Package.objects.get_active_cart(
            user=self.context['user']
        )

    def clean_investments(self):
        investment_ids = self.cleaned_data['investments'].split('-')
        if '' in investment_ids: investment_ids.remove('')
        return investment_ids

    def clean_all_queryset(self):
        return self.cleaned_data['all_queryset'] == 'true'

    def clean(self):
        qs = Investment.objects.filter(project_status=Investment.NOT_FUNDED)
        inv_ids = self.cleaned_data['investments'] if 'investments' in self.cleaned_data else []
        all_queryset = self.cleaned_data['all_queryset']
        self.cleaned_data['investments'] = qs.exclude(id__in=inv_ids) if all_queryset else qs.filter(id__in=inv_ids)

    def save(self):
        investments = list()
        project  = self.cleaned_data['project']
        for inv in self.cleaned_data['investments']:
            self.package.funded_investments.add(inv)
            inv.funded_by = project
            investments.append(inv)
        self.package.project = project
        self.package.save()
        Investment.objects.bulk_update(investments, ['funded_by'])
        return self.package


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

    def __init__(self, *args, **kwargs):
        context = kwargs.pop('context')
        self.user = None
        if context:
            self.user = context.get('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        if self.user is None or not self.user.is_moderator:
            raise Exception("Moderator user required.")

    def save(self):
        package = self.cleaned_data['package']
        if 'reject_reason' in self.cleaned_data and self.cleaned_data['reject_reason'] not in [None, '']:
            package.rejection_reason = self.cleaned_data['reject_reason']
            package.status = Package.REJECTED
            if 'no_resubmission' in self.cleaned_data and self.cleaned_data['no_resubmission']:
                package.status = Package.CLOSED
        else:
            package.status = Package.APPROVED
        package.review_by = self.user
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
