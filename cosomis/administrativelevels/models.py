import json
from django.db import models
from django.utils.translation import gettext_lazy as _
from cosomis.models_base import BaseModel


class AdministrativeLevel(BaseModel):
    """
    field -> priority identified (date)
    Set an Attr(model) as default image
    """
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
    default_image = models.ForeignKey('investments.Attachment', on_delete=models.SET_NULL, null=True, blank=True)
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
    identified_priority = models.DateField(null=True, blank=True)

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


class Phase(BaseModel):
    village = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, related_name='phases')
    order = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        unique_together = ['village', 'order']

    def __str__(self):
        return '%s. %s(%s)' % (self.order, self.name, self.village)

    def get_status(self):
        completed = self.activities.filter(
            tasks__id__in=models.Subquery(
                Task.objects.filter(status=Task.COMPLETED).values('id')
            )
        ).exists()
        not_started = self.activities.filter(
            tasks__id__in=models.Subquery(
                Task.objects.filter(status=Task.NOT_STARTED).values('id')
            )
        ).exists()
        if not_started and not completed:
            return Task.NOT_STARTED
        elif not not_started and completed:
            return Task.COMPLETED
        elif self.activities.filter(
                tasks__id__in=models.Subquery(
                    Task.objects.filter(status=Task.ERROR).values('id')
                )
        ).exists():
            return Task.ERROR
        return Task.IN_PROGRESS

    def get_order(self):
        last_phase = self.__class__.objects.filter(
            village=self.village
        ).aggregate(
            last_phase=models.Max('order')
        )['last_phase'] or 0
        return last_phase + 1

    def save(self, *args, **kwargs):
        if self.order is None:
            self.order = self.get_order()
        return super(Phase, self).save(*args, **kwargs)


class Activity(BaseModel):
    phase = models.ForeignKey(Phase, on_delete=models.CASCADE, related_name='activities')
    order = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()

    class Meta:
        unique_together = ['phase', 'order']

    def __str__(self):
        return '%s. %s(%s)' % (self.order, self.name, self.phase)

    def get_status(self):
        not_started = self.tasks.filter(status=Task.NOT_STARTED).exists()
        completed = self.tasks.filter(status=Task.COMPLETED).exists()
        if not_started and not completed:
            return Task.NOT_STARTED
        elif not not_started and completed:
            return Task.COMPLETED
        elif self.tasks.filter(status=Task.ERROR).exists():
            return Task.ERROR
        return Task.IN_PROGRESS

    def get_order(self):
        last_activity = self.__class__.objects.filter(
            phase=self.phase
        ).aggregate(
            last_activity=models.Max('order')
        )['last_activity'] or 0
        return last_activity + 1

    def save(self, *args, **kwargs):
        if self.order is None:
            self.order = self.get_order()
        return super(Activity, self).save(*args, **kwargs)


class Task(BaseModel):
    NOT_STARTED = 'not started'
    IN_PROGRESS = 'in progress'
    COMPLETED = 'completed'
    ERROR = 'error'

    STATUS = [
        (NOT_STARTED, _(NOT_STARTED)),
        (IN_PROGRESS, _(IN_PROGRESS)),
        (COMPLETED, _(COMPLETED)),
        (ERROR, _(ERROR)),
    ]

    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='tasks')
    order = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=127, choices=STATUS, default=NOT_STARTED)

    form_responses = models.TextField(null=True, blank=True, help_text='This is a json field that needs to be parsed.')

    class Meta:
        unique_together = ['activity', 'order']

    def __str__(self):
        return '%s. %s(%s) - %s' % (self.order, self.name, str(self.activity.id), self.status)

    def get_order(self):
        last_task = self.__class__.objects.filter(
            activity=self.activity
        ).aggregate(
            last_task=models.Max('order')
        )['last_task'] or 0
        return last_task + 1

    def save(self, *args, **kwargs):
        if self.order is None:
            self.order = self.get_order()
        return super(Task, self).save(*args, **kwargs)

    @property
    def dict_form_responses(self):
        return json.loads(str(self.form_responses))


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

