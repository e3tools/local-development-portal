from django import forms
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import Project
from usermanager.models import User
from usermanager.utils import confirm_email_notification
from .models import Package, Investment, PackageFundedInvestment, GroupInvestment


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
        project = self.cleaned_data['project']
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
        if self.user is None or not (self.user.is_moderator or self.user.is_superuser):
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
        package_funded_investments = PackageFundedInvestment.objects.select_related('investment').filter(package_id=package.id)
        released_investments = []
        package_is_rejected = package.status in (Package.REJECTED, Package.CLOSED)
        # CLOSED n'existe pas dans les statuts (P/A/R) d'un item : un paquet clôturé
        # reflète quand même chaque item comme rejeté.
        item_status = PackageFundedInvestment.REJECTED if package_is_rejected else package.status
        for package_item in package_funded_investments:
            package_item.status = item_status
            package_item.rejection_reason = package.rejection_reason
            package_item.save()
            if package_is_rejected:
                # Libérer l'investissement pour qu'il redevienne disponible
                # (catalogue "Financer un projet" et onglets Priorités),
                # comme le fait déjà le rejet ligne par ligne.
                package_item.investment.funded_by = None
                package_item.investment.project_status = Investment.NOT_FUNDED
                released_investments.append(package_item.investment)
        if released_investments:
            Investment.objects.bulk_update(released_investments, ['funded_by', 'project_status'])


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
        confirm_email_notification(self.cleaned_data['user'])


class GroupInvestmentAnomalyEditForm(forms.ModelForm):
    """Used from the anomalies report to correct a market's own fields
    (typically the missing canton/village link that flagged it)."""

    class Meta:
        model = GroupInvestment
        fields = ['title', 'description', 'administrative_level', 'lieu', 'component', 'ranking']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class InvestmentAnomalyEditForm(forms.ModelForm):
    """Used from the anomalies report to correct an Investment's own fields
    (location, classification, status...). Sync-managed bookkeeping fields
    (no_sql_id, imported_project_id, last_sync, came_from) are left out —
    they're overwritten by the next sync and editing them locally wouldn't
    stick."""

    class Meta:
        model = Investment
        fields = [
            'title', 'description', 'responsible_structure',
            'administrative_level', 'administrative_levels', 'sector', 'component',
            'group_investment', 'groupes_socioeconomiques', 'ranking',
            'investment_status', 'project_status', 'funded_by',
            'estimated_cost', 'real_cost', 'beneficiaries',
            'start_date', 'duration', 'delays_consumed',
            'physical_execution_rate', 'financial_implementation_rate',
            'endorsed_by_youth', 'endorsed_by_women', 'endorsed_by_agriculturist',
            'endorsed_by_pastoralist', 'endorsed_by_displaced',
            'climate_contribution', 'climate_contribution_text',
            'latitude', 'longitude', 'abandoned_in_the_meantime',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'climate_contribution_text': forms.Textarea(attrs={'rows': 2}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'administrative_levels': forms.SelectMultiple(),
            'groupes_socioeconomiques': forms.SelectMultiple(),
        }
