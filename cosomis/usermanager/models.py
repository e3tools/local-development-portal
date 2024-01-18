from django.db import models
from django.contrib.auth.models import User
from investments.models import Organization


class UserPassCode(models.Model):
    pass_code = models.CharField(max_length=128)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.user.__str__()


class UserAdditionalConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_conf',)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, related_name='user_conf',
                                     blank=True, null=True)
