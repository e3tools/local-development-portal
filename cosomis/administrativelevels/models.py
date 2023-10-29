from django.db import models
from cdd_client import CddClient
from django.utils.translation import gettext_lazy as _

from financial.models.bank import Bank
from cosomis.models_base import BaseModel

    
class AdministrativeLevel(BaseModel):
    LIME_GREEN = 'lime_green'
    DARK_GREEN = 'dark_green'
    ORANGE = 'orange'
    RED = 'red'
    STATUS_COLORS = (
        (LIME_GREEN, _('Lime Green')),
        (DARK_GREEN, _('Dark Green')),
        (ORANGE, _('Orange')),
        (RED, _('Red'))
    )

    EARLY = 'early'
    NORMAL = 'normal'
    LATE = 'late'
    BLOCKED = 'blocked'
    STATUS_DESCRIPTION = (
        (EARLY, _('Early')),
        (NORMAL, _('Normal')),
        (LATE, _('Late')),
        (BLOCKED, _('Blocked'))
    )

    VILLAGE = 'village'
    CANTON = 'canton'
    COMMUNE = 'commune'
    REGION = 'region'
    PREFECTURE = 'prefecture'
    TYPE = (
        (VILLAGE, _('Village')),
        (CANTON, _('Canton')),
        (COMMUNE, _('Commune')),
        (REGION, _('Region')),
        (PREFECTURE, _('Prefecture'))
    )
    parent = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Parent"))
    geographical_unit = models.ForeignKey('GeographicalUnit', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Geographical unit"))
    cvd = models.ForeignKey('CVD', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("CVD"))
    frontalier = models.BooleanField(default=True, verbose_name=_("Frontalier"))
    rural = models.BooleanField(default=True, verbose_name=_("Rural"))

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Longitude"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    # adm_0_id to adm_n_id
    status_color = models.CharField(max_length=20, choices=STATUS_COLORS, default=LIME_GREEN)
    status_description = models.CharField(max_length=15, choices=STATUS_DESCRIPTION, default=NORMAL)
    type = models.CharField(max_length=255, verbose_name=_("Type"), choices=TYPE, default=VILLAGE)
    total_population = models.IntegerField(default=0)
    population_men = models.IntegerField(default=0)
    population_women = models.IntegerField(default=0)
    population_young = models.IntegerField(default=0)
    population_elder = models.IntegerField(default=0)
    population_handicap = models.IntegerField(default=0)
    population_agriculturist = models.IntegerField(default=0)
    population_pastoralist = models.IntegerField(default=0)
    population_minorities = models.IntegerField(default=0)
    main_languages = models.CharField(max_length=50, blank=True, null=True)

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)
    
    class Meta:
        unique_together = ['name', 'parent', 'type']

    def __str__(self):
        return self.name

    def get_list_priorities(self):
        """Method to get the list of the all priorities that the administrative is linked"""
        return self.villagepriority_set.get_queryset()
    
    # def get_list_subprojects(self):
    #     """Method to get the list of the all subprojects that the administrative is linked"""
    #     return self.subproject_set.get_queryset()
    def get_list_subprojects(self):
        """Method to get the list of the all subprojects that the administrative is linked"""
        if self.cvd:
            return self.cvd.subproject_set.get_queryset()
        return []
    
    def get_facilitator(self, projects_ids):
        for assign in self.assignadministrativeleveltofacilitator_set.get_queryset().filter(project_id__in=projects_ids, activated=True):
            return assign.facilitator
        return None

    def is_village(self):
        return self.type.lower() == self.VILLAGE

    def is_canton(self):
        return self.type.lower() == self.CANTON

    def is_commune(self):
        return self.type.lower() == self.COMMUNE

    def is_region(self):
        return self.type.lower() == self.REGION

    def is_prefecture(self):
        return self.type.lower() == self.PREFECTURE

    @property
    def children(self):
        return self.administrativelevel_set.get_queryset()
    
    def get_list_geographical_unit(self):
        """Method to get the list of the all Geographical Unit that the administrative is linked"""
        return self.geographicalunit_set.get_queryset()


class GeographicalUnit(BaseModel):
    canton = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Administrative level"))
    attributed_number_in_canton = models.IntegerField(verbose_name=_("Attributed number in canton"))
    unique_code = models.CharField(max_length=100, unique=True, verbose_name=_("Unique code"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    class Meta:
        unique_together = ['canton', 'attributed_number_in_canton']

    def get_name(self):
        administrativelevels = self.get_villages()
        name = ""
        count = 1
        length = len(administrativelevels)
        for adl in administrativelevels:
            name += adl.name
            if length != count:
                name += "/"
            count += 1
        return name if name else self.unique_code
    
    def get_villages(self):
        return self.administrativelevel_set.get_queryset()

    def get_cvds(self):
        return self.cvd_set.get_queryset()
    
    def __str__(self):
        return self.get_name()
    

class CVD(BaseModel):
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    geographical_unit = models.ForeignKey('GeographicalUnit', on_delete=models.CASCADE, verbose_name=_("Geographical unit"))
    headquarters_village = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE, related_name='headquarters_village_of_the_cvd', verbose_name=_("Headquarters village"))
    attributed_number_in_canton = models.IntegerField(null=True, blank=True, verbose_name=_("Attributed number in canton"))
    unique_code = models.CharField(max_length=100, verbose_name=_("Unique code"))
    bank = models.ForeignKey(Bank, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Bank"))
    bank_code = models.CharField(max_length=10, verbose_name=_("Bank code"), null=True, blank=True)
    guichet_code = models.CharField(max_length=10, verbose_name=_("Guichet code"), null=True, blank=True)
    account_number = models.CharField(max_length=100, verbose_name=_("Account number"), null=True, blank=True)
    rib = models.CharField(max_length=2, verbose_name=_("RIB"), null=True, blank=True)
    president_name_of_the_cvd = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("President name of the CVD"))
    president_phone_of_the_cvd = models.CharField(max_length=15, null=True, blank=True, verbose_name=_("President phone of the CVD"))
    treasurer_name_of_the_cvd = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Treasurer name of the CVD"))
    treasurer_phone_of_the_cvd = models.CharField(max_length=15, null=True, blank=True, verbose_name=_("Treasurer phone of the CVD"))
    secretary_name_of_the_cvd = models.CharField(max_length=100, null=True, blank=True, verbose_name=_("Secretary name of the CVD"))
    secretary_phone_of_the_cvd = models.CharField(max_length=15, null=True, blank=True, verbose_name=_("Secretary phone of the CVD"))
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))

    def get_name(self):
        administrativelevels = self.get_villages()
        if self.name:
            return self.name
        
        name = ""
        count = 1
        length = len(administrativelevels)
        for adl in administrativelevels:
            name += adl.name
            if length != count:
                name += "/"
            count += 1
        return name if name else self.unique_code
    
    def get_villages(self):
        return self.administrativelevel_set.get_queryset()
    
    def get_canton(self):
        if self.headquarters_village:
            return self.headquarters_village.parent
            
        for obj in self.get_villages():
            return obj.parent
        return None
    
    def get_list_subprojects(self):
        """Method to get the list of the all subprojects"""
        return self.subproject_set.get_queryset()
    
    def __str__(self):
        return self.get_name()


class Project(BaseModel):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    implementation_agency = models.CharField(max_length=255)


class Category(BaseModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)


class Investment(BaseModel):
    NOT_FUNDED = 'N'
    IN_PROGRESS = 'P'
    COMPLETED = 'C'
    PROJECT_STATUS_CHOICES = (
        (NOT_FUNDED, _('Not Funded')),
        (IN_PROGRESS, _('In Progress')),
        (COMPLETED, _('Completed'))
    )

    PRIORITY = 'p'
    SUBPROJECT = 's'
    INVESTMENT_STATUS_CHOICES = (
        (PRIORITY, _('Priority')),
        (SUBPROJECT, _('SubProject'))
    )

    title = models.CharField(max_length=255)
    responsible_structure = models.CharField(max_length=255, null=True, blank=True)
    sector = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='investments')
    estimated_cost = models.PositiveBigIntegerField()
    start_date = models.DateField(null=True)
    duration = models.PositiveIntegerField(help_text=_('In days'))
    delays_consumed = models.PositiveIntegerField(help_text=_('In days'))
    physical_execution_rate = models.PositiveIntegerField(help_text=_('Percentage'))
    financial_implementation_rate = models.PositiveIntegerField(help_text=_('Percentage'))
    # project_manager_id // TBD Probably is the moderator
    investment_status = models.CharField(max_length=30, choices=INVESTMENT_STATUS_CHOICES, default=PRIORITY)
    project_status = models.CharField(max_length=30, choices=PROJECT_STATUS_CHOICES, default=NOT_FUNDED)
    endorsed_by_youth = models.BooleanField(default=False)
    endorsed_by_women = models.BooleanField(default=False)
    endorsed_by_agriculturist = models.BooleanField(default=False)
    endorsed_by_pastoralist = models.BooleanField(default=False)


class Package(BaseModel):
    PENDING_APPROVAL = 'P'
    APPROVED = 'A'
    REJECTED = 'R'
    UNDER_EXECUTION = 'E'
    STATUS = (
        (PENDING_APPROVAL, _('Pending Approval')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (UNDER_EXECUTION, _('Under Execution'))
    )

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='packages')
    source = models.CharField(
        max_length=255,
        help_text=_('Source of the funding, e.g., a particular organization or grant'),
        blank=True, null=True
    )
    funded_investments = models.ManyToManyField(Investment, related_name='packages')
    draft_status = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS, default=PENDING_APPROVAL)


class Attachment(BaseModel):
    PHOTO = 'Photo'
    DOCUMENT = 'Document'
    TYPE_CHOICES = (
        (PHOTO, _('Photo')),
        (DOCUMENT, _('Document'))
    )
    adm = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, related_name='attachments')
    investment = models.ForeignKey(
        Investment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attachments'
    )
    url = models.URLField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DOCUMENT)
    task = models.CharField(max_length=10, blank=False)
    activity = models.CharField(max_length=10, blank=False)
    phase = models.CharField(max_length=10, blank=False)


def update_or_create_amd_couch(sender, instance, **kwargs):
    print("test", instance.id, kwargs['created'])
    client = CddClient()
    if kwargs['created']:
        couch_object_id = client.create_administrative_level(instance)
        to_update = AdministrativeLevel.objects.filter(id=instance.id)
        to_update.update(no_sql_db_id=couch_object_id)
    else:
        client.update_administrative_level(instance)

# def delete_amd_couch(sender, instance, **kwargs):
#     client = CddClient()
#     client.delete_administrative_level(instance)



# post_save.connect(update_or_create_amd_couch, sender=AdministrativeLevel)
# post_delete.connect(delete_amd_couch, sender=AdministrativeLevel) # POST-DELETE method to delete the administrativelevel in the couchdb

