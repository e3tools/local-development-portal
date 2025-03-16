from django.db.models.signals import post_save
from django.dispatch import receiver
from usermanager.utils import sign_up_email_notification
from .models import User


@receiver(post_save, sender=User)
def email_notification_welcome(sender, instance, created, **kwargs):
    if created:
        sign_up_email_notification(instance)