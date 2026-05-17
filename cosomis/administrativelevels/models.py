import json
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from usermanager.models import User, Organization
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

    TYPE = (  # Keep this order, is important for the gallery
        (VILLAGE, _('Village')),
        (CANTON, _('Canton')),
        (COMMUNE, _('Commune')),
        (PREFECTURE, _('Prefecture')),
        (REGION, _('Region'))
    )

    # Different country datasets store the same logical level under different
    # type strings — e.g. the Benin dataset uses 'arrondissement' for Canton
    # and 'département' for Prefecture. All comparisons against `type` go
    # through aliases_for() / type_filter_q() / is_*() so call sites never
    # hard-code a single spelling.
    TYPE_ALIASES = {
        VILLAGE: ('village',),
        CANTON: ('canton', 'arrondissement'),
        COMMUNE: ('commune',),
        PREFECTURE: ('prefecture', 'département', 'departement'),
        REGION: ('region', 'région', 'country'),
    }

    # system properties
    parent = models.ForeignKey('AdministrativeLevel', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Parent"), related_name='children')
    type = models.CharField(max_length=255, verbose_name=_("Type"), choices=TYPE, default=VILLAGE)
    default_image = models.ForeignKey('investments.Attachment', on_delete=models.SET_NULL, null=True, blank=True)
    facilitator = models.CharField(max_length=50, blank=True, null=True)
    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)

    # LDP properties
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    rank = models.PositiveIntegerField(null=True, blank=True)
    rural = models.BooleanField(default=True, verbose_name=_("Rural"))
    frontalier = models.BooleanField(default=True, verbose_name=_("Frontalier"))
    status_color = models.CharField(max_length=20, choices=STATUS_COLORS, default=LIME_GREEN)
    status_description = models.CharField(max_length=15, choices=STATUS_DESCRIPTION, default=NORMAL)
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
    infrastructure = models.JSONField(null=True, blank=True)

    # climate properties

    geographical_unit = models.ForeignKey('GeographicalUnit', null=True, blank=True, on_delete=models.CASCADE, verbose_name=_("Geographical unit"))
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Latitude"))
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, verbose_name=_("Longitude"))
    geo_segment = models.ForeignKey('GeoSegment', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Geo segment"))
    code_loc = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Code location"))
    
    class Meta:
        unique_together = ['name', 'parent', 'type']

    def __str__(self):
        return self.name

    def get_current_task(self):
        if self.is_village():
            phases = Phase.objects.filter(village=self).order_by('-order')
            for phase in phases:
                activities = phase.activities.all().order_by('-order')
                for activity in activities:
                    tasks = activity.tasks.all().order_by('-order')
                    for task in tasks:
                        if task.status == Task.COMPLETED:
                            return task
        else:
            return None

    def get_list_subprojects(self):
        """Method to get the list of the all subprojects that the administrative is linked"""
        if self.cvd:
            return self.cvd.subproject_set.get_queryset()
        return []
    
    def get_facilitator(self, projects_ids):
        for assign in self.assignadministrativeleveltofacilitator_set.get_queryset().filter(project_id__in=projects_ids, activated=True):
            return assign.facilitator
        return None

    @classmethod
    def aliases_for(cls, canonical_type):
        """All lowercase type strings that resolve to the given canonical type."""
        return cls.TYPE_ALIASES.get(canonical_type, (canonical_type.lower(),))

    @classmethod
    def matches_type(cls, stored_type, canonical_type):
        if not stored_type:
            return False
        return stored_type.strip().lower() in cls.aliases_for(canonical_type)

    @classmethod
    def type_filter_q(cls, canonical_type, field="type"):
        """Q expression matching any stored alias of `canonical_type` (case-insensitive)."""
        q = Q()
        for alias in cls.aliases_for(canonical_type):
            q |= Q(**{f"{field}__iexact": alias})
        return q

    @classmethod
    def get_hierarchy_labels(cls):
        """Return the dataset's actual level names, root-first.

        Walks one branch from the root down (root -> first child -> first
        grandchild ...) and collects each node's `type` string. The result
        reflects what the data actually calls each depth (Country / Département
        / Commune / Arrondissement / Village for Benin, Region / Prefecture /
        Commune / Canton / Village for Togo, etc.) so UI labels can be driven
        by the data instead of being hard-coded.
        """
        root = cls.objects.filter(parent__isnull=True).first()
        if not root:
            return []
        labels = []
        cur = root
        seen = set()
        while cur and cur.id not in seen:
            labels.append((cur.type or "").strip().capitalize())
            seen.add(cur.id)
            cur = cur.children.first()
        return labels

    def is_village(self):
        return self.matches_type(self.type, self.VILLAGE)

    def is_canton(self):
        return self.matches_type(self.type, self.CANTON)

    def is_commune(self):
        return self.matches_type(self.type, self.COMMUNE)

    def is_region(self):
        return self.matches_type(self.type, self.REGION)

    def is_prefecture(self):
        return self.matches_type(self.type, self.PREFECTURE)

    @property
    def children(self):
        return self.administrativelevel_set.get_queryset()

    def get_all_descendants(self):
        children = self.children.all()
        all_descendants = list(children)
        for child in children:
            all_descendants += child.get_all_descendants()
        return all_descendants
    
    def get_list_geographical_unit(self):
        """Method to get the list of the all Geographical Unit that the administrative is linked"""
        return self.geographicalunit_set.get_queryset()

    def get_villages_coordinates(self):
        coordinates = list()
        if self.is_village():
            if self.longitude is not None and self.latitude is not None:
                return {
                    "name": self.name,
                    "id": self.id,
                    "coordinates": [float(self.longitude), float(self.latitude)]
                }
        for child in self.children.all():
            if child.is_village():
                if child.longitude is not None and child.latitude is not None:
                    coordinates.append(child.get_villages_coordinates())
            else:
                coordinates += child.get_villages_coordinates()
        return coordinates


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


class GeoSegment(BaseModel):
    latitude_northwest = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Latitude"))
    longitude_northwest = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Longitude"))
    latitude_northeast = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Latitude"))
    longitude_northeast = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Longitude"))
    latitude_southeast = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Latitude"))
    longitude_southeast = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Longitude"))
    latitude_southwest = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Latitude"))
    longitude_southwest = models.DecimalField(max_digits=9, decimal_places=6,db_index=True, blank=True, null=True, verbose_name=_("Longitude"))

    cluster_id = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Cluster ID"))
    country = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Country code"))
    lc_gencat_20 = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("LC gencat 20"))
    region = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Region"))
    acled_bexrem_sum = models.FloatField(blank=True, null=True)
    acled_civvio_sum = models.FloatField(blank=True, null=True)
    acled_riodem_sum = models.FloatField(blank=True, null=True)
    fatal_sum = models.FloatField(blank=True, null=True)
    grid_id = models.IntegerField(blank=True, null=True, verbose_name=_("Grid ID"))
    popplace_travel = models.FloatField(blank=True, null=True)
    population_20 = models.FloatField(blank=True, null=True)
    population_2000_diff = models.FloatField(blank=True, null=True)
    pr_avg_2020_diff = models.FloatField(blank=True, null=True)
    road_len = models.FloatField(blank=True, null=True)
    tmmx_avg_2020_diff = models.FloatField(blank=True, null=True)

    def is_coordinate_inside_geosegment(self, point_coord):
        # lat 8.807737
        # lon 1.578550
        x, y = point_coord
        polygon_coords = [
            [float(self.latitude_northwest), float(self.longitude_northwest)], [float(self.latitude_northeast), float(self.longitude_northeast)],
            [float(self.latitude_southeast), float(self.longitude_southeast)], [float(self.latitude_southwest), float(self.longitude_southwest)]
        ]
        n = len(polygon_coords)
        inside = False

        # Iterate over each edge of the polygon
        for i in range(n):
            x1, y1 = polygon_coords[i]
            x2, y2 = polygon_coords[(i + 1) % n]

            # Check if the point is between the y-coordinates of the polygon edge
            if (y1 > y) != (y2 > y):
                # Calculate the intersection point of the ray with the polygon edge
                intersection_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                # Toggle inside if the point is to the left of the intersection
                if x < intersection_x:
                    inside = not inside

        return inside

    @classmethod
    def sort_coordinates(cls, coords):

        # Find extremes for each direction
        north = max(coords, key=lambda x: x[1])
        south = min(coords, key=lambda x: x[1])
        west = min(coords, key=lambda x: x[0])
        east = max(coords, key=lambda x: x[0])

        # Determine the four corner points
        northwest = max([north, west], key=lambda x: (x[1], -x[0]))  # Max latitude, min longitude for NW
        northeast = max([north, east], key=lambda x: (x[1], x[0]))  # Max latitude, max longitude for NE
        southeast = min([south, east], key=lambda x: (x[1], x[0]))  # Min latitude, max longitude for SE
        southwest = min([south, west], key=lambda x: (x[1], -x[0]))  # Min latitude, min longitude for SW

        return [northwest, northeast, southeast, southwest]


class Category(BaseModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name


class Sector(BaseModel):
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Project(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     null=True, blank=True, related_name="projects",
                                     verbose_name=_("Implementation agency"))

    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    start_date = models.DateField(null=True, blank=True, verbose_name=_("Start date"))
    end_date = models.DateField(null=True, blank=True, verbose_name=_("End date"))
    total_amount = models.PositiveBigIntegerField(default=0)
    sectors = models.ManyToManyField(Category, verbose_name=_("Sectors"))
    implementation_partner = models.TextField(null=True, blank=True, help_text=_("e.g., WORLD BANK,UNFPA,WFP"), verbose_name=_("Implementation partner"))
    source_of_financing = models.CharField(_("Source of financing"), null=True, blank=True, max_length=255)


class Phase(BaseModel):
    village = models.ForeignKey(AdministrativeLevel, on_delete=models.CASCADE, related_name='phases')
    order = models.PositiveIntegerField(blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)

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
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)

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
    no_sql_db_id = models.CharField(null=True, blank=True, max_length=255)
    form_responses = models.JSONField(null=True, blank=True)
    form = models.JSONField(null=True, blank=True)

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
        try:
            return json.loads(str(self.form_responses))
        except json.JSONDecodeError as e:
            return dict()


# def update_or_create_amd_couch(sender, instance, **kwargs):
#     print("test", instance.id, kwargs['created'])
#     client = CddClient()
#     if kwargs['created']:
#         couch_object_id = client.create_administrative_level(instance)
#         to_update = AdministrativeLevel.objects.filter(id=instance.id)
#         to_update.update(no_sql_db_id=couch_object_id)
#     else:
#         client.update_administrative_level(instance)

# def delete_amd_couch(sender, instance, **kwargs):
#     client = CddClient()
#     client.delete_administrative_level(instance)



# post_save.connect(update_or_create_amd_couch, sender=AdministrativeLevel)
# post_delete.connect(delete_amd_couch, sender=AdministrativeLevel) # POST-DELETE method to delete the administrativelevel in the couchdb

