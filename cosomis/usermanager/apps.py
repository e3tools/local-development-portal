from django.apps import AppConfig


class UsermanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'usermanager'

    def ready(self):
        from . import signals
