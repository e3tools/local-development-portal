from django.db import models
from django.utils.translation import gettext_lazy as _
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

    VILLAGE = 'Village'
    CANTON = 'Canton'
    COMMUNE = 'Commune'
    REGION = 'Region'
    PREFECTURE = 'Prefecture'
    TYPE = (
        (VILLAGE, _('Village')),
        (CANTON, _('Canton')),
        (COMMUNE, _('Commune')),
        (REGION, _('Region')),
        (PREFECTURE, _('Prefecture'))
    )
    parent = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Parent"))
    geographical_unit = models.ForeignKey('GeographicalUnit', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Geographical unit"))
    frontalier = models.BooleanField(default=True, verbose_name=_("Frontalier"))
    rural = models.BooleanField(default=True, verbose_name=_("Rural"))

    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Longitude"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    rank = models.PositiveIntegerField(null=True, blank=True)
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
        return self.type.lower() == self.VILLAGE.lower()

    def is_canton(self):
        return self.type.lower() == self.CANTON.lower()

    def is_commune(self):
        return self.type.lower() == self.COMMUNE.lower()

    def is_region(self):
        return self.type.lower() == self.REGION.lower()

    def is_prefecture(self):
        return self.type.lower() == self.PREFECTURE.lower()

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


class Project(BaseModel):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    implementation_agency = models.CharField(max_length=255)


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

