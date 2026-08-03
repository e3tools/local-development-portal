from boto3.session import Session
from botocore.exceptions import NoCredentialsError, ClientError
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from cosomis.models_base import BaseModel
from django.utils.translation import gettext_lazy as _

from administrativelevels.models import AdministrativeLevel, Project, Task, Sector
from usermanager.models import User


class PackageQuerySet(models.QuerySet):
    def get_active_cart(self, user):
        """Get active invoice for user"""
        qs = self.model.objects.filter(user=user, status=Package.PENDING_SUBMISSION)
        package = qs.last()
        if qs.count() > 1:
            qs = qs.exclude(id=package.id)
            for obj in qs:
                obj.status = Package.REJECTED
                obj.save()
        elif qs.count() < 1:
            return self.model.objects.create(
                user=user, status=Package.PENDING_SUBMISSION
            )
        return package


class Investment(BaseModel): # Investment module
    NOT_FUNDED = "N"
    FUNDED = "F"
    IN_PROGRESS = "P"
    COMPLETED = "C"
    PAUSED = "PA"
    PROJECT_STATUS_CHOICES = (
        (NOT_FUNDED, _("Not Funded")),
        (FUNDED, _("Funded")),
        (IN_PROGRESS, _("In Progress")),
        (COMPLETED, _("Completed")),
        (PAUSED, _("Paused")),
    )

    PRIORITY = "p"
    SUBPROJECT = "s"
    INVESTMENT_STATUS_CHOICES = (
        (PRIORITY, _("Priority")),
        (SUBPROJECT, _("SubProject")),
    )
    ranking = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    responsible_structure = models.CharField(max_length=255, null=True, blank=True)
    administrative_level = models.ForeignKey(
        AdministrativeLevel, on_delete=models.CASCADE, related_name="investments"
    )
    sector = models.ForeignKey(
        Sector, on_delete=models.CASCADE, related_name="investments"
    )
    estimated_cost = models.PositiveBigIntegerField()
    real_cost = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True)
    came_from = models.ManyToManyField(
        Project,
        related_name="projects_investments",
        default=[],
        blank=True,
    )
    
    duration = models.PositiveIntegerField(help_text=_("In days"))
    delays_consumed = models.PositiveIntegerField(help_text=_("In days"))
    physical_execution_rate = models.PositiveIntegerField(help_text=_("Percentage"))
    financial_implementation_rate = models.PositiveIntegerField(
        help_text=_("Percentage")
    )
    # project_manager_id // TBD Probably is the moderator
    investment_status = models.CharField(
        max_length=30, choices=INVESTMENT_STATUS_CHOICES, default=PRIORITY
    )
    project_status = models.CharField(
        max_length=30, choices=PROJECT_STATUS_CHOICES, default=NOT_FUNDED
    )
    endorsed_by_youth = models.BooleanField(default=False)
    endorsed_by_women = models.BooleanField(default=False)
    endorsed_by_agriculturist = models.BooleanField(default=False)
    endorsed_by_pastoralist = models.BooleanField(default=False)
    climate_contribution = models.BooleanField(default=False)
    climate_contribution_text = models.TextField(null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True, verbose_name=_("Latitude"))
    longitude = models.FloatField(null=True, blank=True, verbose_name=_("Longitude"))
    funded_by = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="investments",
        null=True,
        blank=True,
    )
    no_sql_id = models.CharField(max_length=255)
    imported_project_id = models.CharField(max_length=255, null=True, blank=True)

    abandoned_in_the_meantime = models.BooleanField(default=False)
    abandonment_history = models.JSONField(null=True, blank=True)

    def get_projects_priority_came_from(self, join_on_chain=True):
        projects = self.came_from.all()
        if join_on_chain:
            return ", ".join([p.name for p in projects])
        else:
            return projects

    def get_last_rejection(self):
        """Most recent rejected package claim on this investment (organization + reason).

        Only relevant while the investment is available again (no current
        funded_by) — an investment currently claimed by a partner doesn't
        need its past rejection history surfaced.
        """
        if self.funded_by_id is not None:
            return None
        pfi = (
            PackageFundedInvestment.objects
            .filter(investment_id=self.pk, status=PackageFundedInvestment.REJECTED)
            .select_related('package__project__organization')
            .order_by('-updated_date')
            .first()
        )
        if pfi is None:
            return None
        return {
            'organization': pfi.package.project.organization if pfi.package.project_id else None,
            'reason': pfi.rejection_reason,
        }

    def __str__(self):
        return f'{self.title}'


class Package(BaseModel):  # investments module (orden de compra(cart de invesments(products)))
    PENDING_SUBMISSION = "PS"
    PENDING_APPROVAL = "P"
    APPROVED = "A"
    REJECTED = "R"
    UNDER_EXECUTION = "E"
    PARTIALLY_APPROVED = "PA"
    SELECTED_BY_GOVERNMENT = "SG"
    CLOSED = "C"
    STATUS = (
        (PENDING_SUBMISSION, _("Pending Submission")),
        (PENDING_APPROVAL, _("Pending Approval")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
        (UNDER_EXECUTION, _("Under Execution")),
        (PARTIALLY_APPROVED, _("Partially Processed")),
        (SELECTED_BY_GOVERNMENT, _("Selected by Government")),
        (CLOSED, _("Closed")),
    )

    objects = PackageQuerySet.as_manager()

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="packages",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="packages")
    source = models.CharField(
        max_length=255,
        help_text=_("Source of the funding, e.g., a particular organization or grant"),
        blank=True,
        null=True,
    )
    funded_investments = models.ManyToManyField(Investment, through="PackageFundedInvestment", related_name="packages")
    draft_status = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS, default=PENDING_SUBMISSION)
    acknowledge_by_investor = models.BooleanField(default=False)

    review_by = models.ForeignKey(User, on_delete=models.SET_NULL,
                                  help_text=_("User who reviews the status of the Package. This user must be a moderator."),
                                  null=True, blank=True)

    rejection_reason = models.TextField(null=True, blank=True)

    def estimated_final_cost(self):
        return self.funded_investments.all().aggregate(
            estimated_final_cost=models.Sum("estimated_cost")
        )["estimated_final_cost"]


class PackageFundedInvestment(BaseModel):
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    investment = models.ForeignKey(Investment, on_delete=models.CASCADE)
    PENDING_APPROVAL = "P"
    APPROVED = "A"
    REJECTED = "R"
    STATUS = (
        (PENDING_APPROVAL, _("Pending Approval")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
    )

    status = models.CharField(max_length=50, choices=STATUS, default=PENDING_APPROVAL)
    rejection_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "investments_package_funded_investments"

    def approve(self):
        with transaction.atomic():
            self.status = self.APPROVED
            self.save()
            self.update_package_status()

    def reject(self, reason=None):
        with transaction.atomic():
            self.status = self.REJECTED
            if reason:
                self.rejection_reason = reason
            self.save()
            # Remettre funded_by à None et le statut à "Non Financé" pour que
            # l'investissement rejeté redevienne disponible partout (catalogue
            # "Financer un projet" et onglets Priorités village/commune/canton)
            self.investment.funded_by = None
            self.investment.project_status = Investment.NOT_FUNDED
            self.investment.save(update_fields=["funded_by", "project_status"])
            self.update_package_status()

    def update_package_status(self):
        packages = PackageFundedInvestment.objects.filter(package_id=self.package_id)
        pending = packages.filter(status__in=self.PENDING_APPROVAL).count()
        approved = packages.filter(status__in=self.APPROVED).count()
        rejected = packages.filter(status__in=self.REJECTED).count()

        if pending > 0:
            # Dès qu'au moins un élément a été traité, le paquet est "Partiellement
            # approuvé" (et reste consultable/actionnable pour le reste) plutôt que
            # de rester "En attente d'approbation" jusqu'à ce que tout soit traité.
            self.package.status = (
                self.package.PARTIALLY_APPROVED
                if (approved > 0 or rejected > 0)
                else self.package.PENDING_APPROVAL
            )

        elif approved > 0 and rejected == 0:
            self.package.status = self.package.APPROVED

        elif rejected > 0 and approved == 0:
            self.package.status = self.package.REJECTED

        elif rejected > 0 and approved > 0:
            self.package.status = self.package.PARTIALLY_APPROVED

        self.package.save()


@receiver(m2m_changed, sender=Package.funded_investments.through)
def sync_investment_status_on_selection(sender, instance, action, pk_set, reverse, **kwargs):
    """Garde Investment.project_status synchronisé avec sa présence dans un panier.

    Dès qu'un partenaire sélectionne un investissement (quel que soit l'écran :
    catalogue "Financer un projet" ou onglets Priorités village/commune/canton),
    celui-ci passe à FUNDED pour qu'il disparaisse partout des listes en attente
    de financement. S'il est retiré avant traitement par un modérateur, il repasse
    à NOT_FUNDED et funded_by est réinitialisé pour redevenir disponible.
    """
    if reverse:
        # Ce signal ne gère que le sens Package -> Investments utilisé par l'app.
        return

    if action == "pre_clear":
        instance._investments_before_clear = list(
            instance.funded_investments.values_list("pk", flat=True)
        )
        return

    if action == "post_add" and pk_set:
        # Ne "promeut" que les investissements encore Non Financé : n'écrase jamais
        # un statut déjà plus avancé (ex. import en masse déjà En cours/Terminé).
        Investment.objects.filter(
            pk__in=pk_set, project_status=Investment.NOT_FUNDED
        ).update(project_status=Investment.FUNDED)

    elif action == "post_remove" and pk_set:
        Investment.objects.filter(pk__in=pk_set).update(
            project_status=Investment.NOT_FUNDED, funded_by=None
        )

    elif action == "post_clear":
        investment_ids = getattr(instance, "_investments_before_clear", [])
        if investment_ids:
            Investment.objects.filter(pk__in=investment_ids).update(
                project_status=Investment.NOT_FUNDED, funded_by=None
            )


class Attachment(BaseModel):
    """
    parent info and tasks info
    """
    AWS_STORAGE_BUCKET_NAME = settings.AWS_STORAGE_BUCKET_NAME
    AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

    PHOTO = "Photo"
    DOCUMENT = "Document"
    TYPE_CHOICES = ((PHOTO, _("Photo")), (DOCUMENT, _("Document")))

    COMMUNITY_PROCESS = "Community Process" 
    INFRASTRUCTURE_IN_PROGRESS = "Infrastructure in Progress"
    COMPLETED_INFRASTRUCTURE = "Completed Infrastructure"

    PROCESS_MOMENTS = (
        (COMMUNITY_PROCESS, _("Community Process")),
        (INFRASTRUCTURE_IN_PROGRESS, _("Infrastructure in Progress")),
        (COMPLETED_INFRASTRUCTURE, _("Completed Infrastructure")),
    )

    adm = models.ForeignKey(
        AdministrativeLevel, on_delete=models.CASCADE, related_name="attachments", null=True, blank=True
    )
    investment = models.ForeignKey(
        Investment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    url = models.URLField(max_length=300)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DOCUMENT)
    process_moment = models.CharField(max_length=50, choices=PROCESS_MOMENTS, default=COMMUNITY_PROCESS)

    name = models.CharField(max_length=255, null=True, blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    
    source = models.CharField(max_length=30, null=True, blank=True)

    @classmethod
    def investment_upload(cls, investment, image, object_name=None):
        import logging
        logger = logging.getLogger(__name__)

        if image is None:
            return False, "No image provided"

        if object_name is None:
            object_name = os.path.basename(image.name)

        # Accès sécurisé à l'administrative_level
        try:
            adm = investment.administrative_level
        except Exception:
            adm = None

        # --- Tentative d'upload S3 (ignorée si DEBUG=True) ---
        if not settings.DEBUG:
            try:
                from botocore.config import Config as BotoConfig
                s3_client = Session(
                    aws_access_key_id=cls.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=cls.AWS_SECRET_ACCESS_KEY
                ).client("s3", config=BotoConfig(connect_timeout=5, read_timeout=10))
                image.seek(0)
                s3_client.upload_fileobj(image, cls.AWS_STORAGE_BUCKET_NAME, object_name)
                file_url = f"https://{cls.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{object_name}"

                new_attachment = cls.objects.create(
                    name=object_name,
                    type=cls.PHOTO,
                    process_moment=cls.COMPLETED_INFRASTRUCTURE,
                    investment=investment,
                    adm=adm,
                    url=file_url,
                )
                return True, new_attachment

            except Exception as s3_err:
                logger.warning(
                    "S3 upload failed for investment %s (%s: %s) — falling back to local storage.",
                    investment.id, type(s3_err).__name__, s3_err
                )
        else:
            logger.info(
                "DEBUG mode: skipping S3 for investment %s, using local storage directly.",
                investment.id
            )

        # --- Stockage local dans media/ (utilise FileSystemStorage explicitement) ---
        try:
            from django.core.files.storage import FileSystemStorage
            safe_name = os.path.basename(object_name)
            rel_path = '/'.join(['attachments', 'investments', str(investment.id), safe_name])

            # Créer le répertoire cible explicitement
            target_dir = os.path.join(
                settings.MEDIA_ROOT, 'attachments', 'investments', str(investment.id)
            )
            os.makedirs(target_dir, exist_ok=True)

            # Utiliser FileSystemStorage directement (pas default_storage = S3)
            fs = FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)
            image.seek(0)
            saved_path = fs.save(rel_path, ContentFile(image.read()))
            # Normaliser les séparateurs en forward-slash pour l'URL (Windows)
            saved_path_url = saved_path.replace(os.sep, '/')
            file_url = settings.MEDIA_URL.rstrip('/') + '/' + saved_path_url

            new_attachment = cls.objects.create(
                name=safe_name,
                type=cls.PHOTO,
                process_moment=cls.COMPLETED_INFRASTRUCTURE,
                investment=investment,
                adm=adm,
                url=file_url,
                source='local',
            )
            logger.info(
                "Investment %s: image saved locally at %s", investment.id, file_url
            )
            return True, new_attachment
        except Exception as local_err:
            logger.error(
                "Local storage failed for investment %s: %s",
                investment.id, local_err, exc_info=True
            )
            return False, str(local_err)
