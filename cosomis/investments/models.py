from boto3.session import Session
from django.db import models
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
    IN_PROGRESS = "P"
    COMPLETED = "C"
    PROJECT_STATUS_CHOICES = (
        (NOT_FUNDED, _("Not Funded")),
        (IN_PROGRESS, _("In Progress")),
        (COMPLETED, _("Completed")),
    )

    PRIORITY = "p"
    SUBPROJECT = "s"
    INVESTMENT_STATUS_CHOICES = (
        (PRIORITY, _("Priority")),
        (SUBPROJECT, _("SubProject")),
    )
    ranking = models.PositiveIntegerField(null=True, blank=True)
    title = models.CharField(max_length=255)
    responsible_structure = models.CharField(max_length=255, null=True, blank=True)
    administrative_level = models.ForeignKey(
        AdministrativeLevel, on_delete=models.CASCADE, related_name="investments"
    )
    sector = models.ForeignKey(
        Sector, on_delete=models.CASCADE, related_name="investments"
    )
    estimated_cost = models.PositiveBigIntegerField()
    start_date = models.DateField(null=True)
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
    no_sql_id = models.CharField(max_length=255)
    def __str__(self):
        return f'{self.title}'


class Package(BaseModel):  # investments module (orden de compra(cart de invesments(products)))
    PENDING_SUBMISSION = "PS"
    PENDING_APPROVAL = "P"
    APPROVED = "A"
    REJECTED = "R"
    UNDER_EXECUTION = "E"
    STATUS = (
        (PENDING_SUBMISSION, _("Pending Submission")),
        (PENDING_APPROVAL, _("Pending Approval")),
        (APPROVED, _("Approved")),
        (REJECTED, _("Rejected")),
        (UNDER_EXECUTION, _("Under Execution")),
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
    funded_investments = models.ManyToManyField(Investment, related_name="packages")
    draft_status = models.BooleanField(default=True)
    status = models.CharField(max_length=50, choices=STATUS, default=PENDING_SUBMISSION)

    rejection_reason = models.TextField(null=True, blank=True)

    def estimated_final_cost(self):
        return self.funded_investments.all().aggregate(
            estimated_final_cost=models.Sum("estimated_cost")
        )["estimated_final_cost"]


class Attachment(BaseModel):
    """
    parent info and tasks info
    """

    PHOTO = "Photo"
    DOCUMENT = "Document"
    TYPE_CHOICES = ((PHOTO, _("Photo")), (DOCUMENT, _("Document")))
    adm = models.ForeignKey(
        AdministrativeLevel, on_delete=models.CASCADE, related_name="attachments"
    )
    investment = models.ForeignKey(
        Investment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments",
    )
    task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    url = models.URLField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=DOCUMENT)

    file_path = "aux/test.png"
    bucket_name = "cddfiles"
    object_name = "proof_of_work_thumbnails/image.jpg"

    def get_thumbnail(self):
        s3_client = Session(aws_access_key_id="", aws_secret_access_key="").client("s3")

        # try:
        #     # Download the image from the URL
        #     response = requests.get(str(self.url).split("?")[0])
        #     response.raise_for_status()
        #
        #     # Open the image from the downloaded content
        #     with Image.open(BytesIO(response.content)) as img:
        #         # Create a thumbnail
        #         thumbnail = img.copy()
        #         thumbnail.thumbnail((100, 100))
        #
        #         # Save the thumbnail
        #         thumbnail.save('aux/test.png', format="PNG")
        #         print(f"Thumbnail created and saved at: 'aux/'")
        #
        # except Exception as e:
        #     print(f"Error: {e}")

        try:
            response = s3_client.upload_file(
                self.file_path, self.bucket_name, self.object_name
            )
            print(f"File uploaded successfully. Response: {response}")

        except Exception as e:
            print(f"Error: {e}")
        return
