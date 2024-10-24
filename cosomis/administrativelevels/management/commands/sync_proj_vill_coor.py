from django.core.management.base import BaseCommand
from administrativelevels.models import AdministrativeLevel
from investments.models import Investment


class Command(BaseCommand):
    help = 'Syncronize the project coordinates with the respective village coordinates'

    def handle(self, *args, **options):
        administrative_levels_qs = AdministrativeLevel.objects.exclude(latitude=None, longitude=None)
        investments = Investment.objects.filter(administrative_level__id__in=[administrative_level_object.id for administrative_level_object in administrative_levels_qs])

        for investment in investments:
            investment.latitude, investment.longitude = investment.administrative_level.latitude, investment.administrative_level.longitude

        Investment.objects.bulk_update(investments, ['latitude', 'longitude'])
