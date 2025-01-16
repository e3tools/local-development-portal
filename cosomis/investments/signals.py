from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from usermanager.utils import package_status_email_notification
from .models import Package


@receiver(pre_save, sender=Package)
def email_notification_track(sender, instance, **kwargs):
    try:
        # Fetch the existing instance from the database
        old_instance = sender.objects.get(pk=instance.pk)
    except ObjectDoesNotExist:
        # If the object doesn't exist yet, it's being created, not updated
        return

    if old_instance.status != instance.status:
        # print(f"The field 'name' changed from '{old_instance.status}' to '{instance.status}'")
        # if instance.status == Package.REJECTED:
        #     raise TypeError('The field "status" must be set to "Package.REJECTED"')
        package_status_email_notification(instance)