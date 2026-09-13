"""The demo seeder must be safe to re-run on an already-seeded database."""

from django.core.management import call_command
from django.test import TestCase

from administrativelevels.models import AdministrativeLevel
from investments.models import Investment
from usermanager.models import User


class SeedTogoDemoTests(TestCase):
    def test_reset_rebuilds_the_same_dataset_on_a_seeded_database(self):
        call_command("seed_togo_demo", villages=12, verbosity=0)
        first = (AdministrativeLevel.objects.count(), Investment.objects.count(),
                 User.objects.count())
        # The first live reset failed here: the superuser survived the wipe
        # and was created again, violating the unique username.
        call_command("seed_togo_demo", villages=12, reset=True, verbosity=0)
        second = (AdministrativeLevel.objects.count(), Investment.objects.count(),
                  User.objects.count())
        self.assertEqual(first, second)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_costs_are_stored_in_fcfa_not_thousands(self):
        call_command("seed_togo_demo", villages=6, verbosity=0)
        cheapest = Investment.objects.order_by("estimated_cost").first()
        self.assertGreaterEqual(cheapest.estimated_cost, 4_000_000)
