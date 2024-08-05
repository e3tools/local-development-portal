import csv
from io import TextIOWrapper
from django import forms
from django.forms import RadioSelect, Select

from investments.models import Attachment, Package, Investment
from .models import AdministrativeLevel, Project, Sector
from django.core.exceptions import NON_FIELD_ERRORS
from django.utils.translation import gettext_lazy as _


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        exclude = ['id', 'created_date', 'updated_date', 'owner']

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.owner = self.owner
        return super().save(commit=commit)


class BulkUploadInvestmentsForm(forms.Form):
    csv_file = forms.FileField()
    headers = [
        'village_id',
        'ranking',
        'title',
        'responsible_structure',
        'sector_id',
        'estimated_cost',
        'start_date',
        'duration',
        'delays_consumed',
        'physical_execution_rate',
        'financial_implementation_rate',
        'investment_status',
        'project_status',
        'endorsed_by_youth',
        'endorsed_by_women',
        'endorsed_by_agriculturist',
        'endorsed_by_pastoralist',
        'climate_contribution',
        'climate_contribution_text'
    ]

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)

    def save(self):
        project = self.project
        package = project.packages.all().first()
        init_headers = self.headers
        investments = list()

        package = package if package is not None else Package.objects.create(
            project=project,
            user=project.owner
        )

        # Get the uploaded file
        uploaded_file = self.cleaned_data['csv_file']

        # Open the file as a text stream
        file_stream = TextIOWrapper(uploaded_file.file, encoding='utf-8')

        # Read the CSV file
        csv_reader = csv.reader(file_stream)

        # Process the CSV data
        headers_dict = {}
        for idx, row in enumerate(csv_reader):
            if idx == 0:
                for k, header in enumerate(row):
                    if header in init_headers:
                        headers_dict[header] = k
                        init_headers.remove(header)
            else:
                investments.append(Investment(
                    ranking=row[headers_dict['ranking']],
                    title=row[headers_dict['title']],
                    responsible_structure=row[headers_dict['responsible_structure']],
                    administrative_level=AdministrativeLevel.objects.get(id=row[headers_dict['village_id']]),
                    sector=Sector.objects.get(id=row[headers_dict['sector_id']]),
                    estimated_cost=row[headers_dict['estimated_cost']],
                    start_date=row[headers_dict['start_date']],
                    duration=row[headers_dict['duration']],
                    delays_consumed=row[headers_dict['delays_consumed']],
                    physical_execution_rate=row[headers_dict['physical_execution_rate']],
                    financial_implementation_rate=row[headers_dict['financial_implementation_rate']],
                    investment_status=row[headers_dict['investment_status']],
                    project_status=row[headers_dict['project_status']],
                    endorsed_by_youth=row[headers_dict['endorsed_by_youth']],
                    endorsed_by_women=row[headers_dict['endorsed_by_women']],
                    endorsed_by_agriculturist=row[headers_dict['endorsed_by_agriculturist']],
                    endorsed_by_pastoralist=row[headers_dict['endorsed_by_pastoralist']],
                    climate_contribution=row[headers_dict['climate_contribution']],
                    climate_contribution_text=row[headers_dict['climate_contribution_text']],
                ))

        Investment.objects.bulk_create(investments)
        for investment in investments:
            package.funded_investments.add(investment)

        # Here you can process the data as needed
        # For example, you can save it to the database or process it further

        return project


class AdministrativeLevelForm(forms.ModelForm):
    def __init__(self, parent: str = None, type: str = None, *args, **kwargs):
        super(AdministrativeLevelForm, self).__init__(*args, **kwargs)
        for label, field in self.fields.items():
            self.fields[label].widget.attrs.update({"class": "form-control"})
            if label == "parent":
                print("******* ", parent)
                self.fields[label].queryset = AdministrativeLevel.objects.filter(
                    type=parent
                )
                self.fields[label].label = parent
            if label == "type":
                self.fields[label].initial = type
                print("######### ", parent)

    class Meta:
        model = AdministrativeLevel
        exclude = [
            "no_sql_db_id",
            "geographical_unit",
            "cvd",
            "latitude",
            "longitude",
            "frontalier",
            "rural",
        ]  # specify the fields to be hid


# SearchVillages
class VillageSearchForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Region"),
        required=False,
        empty_label=_("Toutes les régions"),
        label=_("Region"),
    )
    prefecture = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Prefecture"),
        required=False,
        label=_("Prefecture"),
    )
    commune = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Commune"),
        required=False,
        label=_("Commune"),
    )
    canton = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type="Canton"),
        required=False,
        label=_("Canton"),
    )

class FinancialPartnerForm(forms.Form):
    name = forms.CharField()
    is_full_contribution = forms.BooleanField()
    potential_date = forms.DateField()
    commentaries = forms.CharField(widget=forms.Textarea())


class AttachmentFilterForm(forms.Form):
    TYPE_CHOICES = (
        (Attachment.PHOTO, _("Photo")),
        (Attachment.DOCUMENT, _("Document")),
        (None, _("Both")),
    )
    type = forms.ChoiceField(choices=TYPE_CHOICES, widget=RadioSelect, label=_("Type"))
    phase = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Phase"))
    activity = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Activity"))
    task = forms.ChoiceField(widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Task"))
    administrative_level = forms.ModelChoiceField(
        queryset=AdministrativeLevel.objects.filter(type=AdministrativeLevel.VILLAGE),
        widget=Select(attrs={'empty-option': '---------'}), required=False, label=_("Administrative level")
    )
