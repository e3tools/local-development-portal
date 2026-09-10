"""Request every major portal page and fail if any of them errors.

The demo deployment has no test suite standing between a bad commit and a
live URL, so this walks the real view stack — templates, context processors,
template tags and all — against whatever is in the database and reports the
status code of each page. CI runs it after seeding; it is also the quickest
way to check a deployment by hand:

    python manage.py demo_smoke_test
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from administrativelevels.models import AdministrativeLevel


class Command(BaseCommand):
    help = "Request every major portal page and report failures."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@coso-demo.tg")
        parser.add_argument("--password", default="DemoCOSO2026!")
        parser.add_argument(
            "--investor-email", default="banque.mondiale@coso-demo.tg",
            help=(
                "Account used for the investor-only pages, which moderators "
                "are deliberately denied (see IsInvestorMixin)."
            ),
        )

    def handle(self, *args, **options):
        User = get_user_model()
        if not User.objects.filter(email=options["email"]).exists():
            raise CommandError(
                f"No account {options['email']}; run `seed_togo_demo` first."
            )

        client = Client()
        if not client.login(email=options["email"], password=options["password"]):
            raise CommandError("Could not sign in with the supplied credentials.")

        # Investor-only views 403 for moderators by design, so they are checked
        # through a second, non-moderator session rather than skipped.
        investor = Client()
        if not investor.login(
            email=options["investor_email"], password=options["password"]
        ):
            raise CommandError(
                f"Could not sign in as {options['investor_email']}."
            )

        def first(level_type):
            level = AdministrativeLevel.objects.filter(
                AdministrativeLevel.type_filter_q(level_type)
            ).first()
            if level is None:
                raise CommandError(f"No {level_type} in the database.")
            return level

        village = first(AdministrativeLevel.VILLAGE)
        canton = first(AdministrativeLevel.CANTON)
        commune = first(AdministrativeLevel.COMMUNE)
        prefecture = first(AdministrativeLevel.PREFECTURE)
        region = first(AdministrativeLevel.REGION)

        pages = [
            ("Investment catalogue", "/fr/investments/"),
            ("Moderator approvals", "/fr/investments/moderator/notifications"),
            ("Administrative levels", "/fr/administrative-levels/"),
            ("Locality search", "/fr/administrative-levels/search/"),
            ("Photo gallery", "/fr/administrative-levels/attachments/"),
            ("Village profile",
             f"/fr/administrative-levels/village/{village.id}/"),
            ("Canton profile",
             f"/fr/administrative-levels/canton/{canton.id}/"),
            ("Canton planning summary",
             f"/fr/administrative-levels/canton/{canton.id}/planning-summary/"),
            ("Canton map", f"/fr/administrative-levels/canton/{canton.id}/map/"),
            ("Commune profile",
             f"/fr/administrative-levels/commune/{commune.id}/"),
            ("Prefecture profile",
             f"/fr/administrative-levels/prefecture/{prefecture.id}/"),
            ("Region profile",
             f"/fr/administrative-levels/region/{region.id}/"),
            ("Dashboard", "/fr/dashboard/"),
            ("Dashboard summary", "/fr/dashboard/dashboard-summary/"),
            ("Dashboard localities", "/fr/dashboard/administrativelevels/"),
            ("CDD funnel", "/fr/cdd-funnel/"),
            ("Django admin", "/fr/admin/"),
            ("Assistant", "/fr/assistant/"),
        ]

        # (name, url, session) — most pages are checked as the administrator.
        pages = [(name, url, client) for name, url in pages] + [
            ("Funding cart", "/fr/investments/cart", investor),
            ("User profile", "/fr/investments/profile", investor),
            ("Investor approvals",
             "/fr/investments/investor/notifications", investor),
            ("Programmes", "/fr/administrative-levels/projects/", investor),
            ("Assistant (partner)", "/fr/assistant/", investor),
        ]

        failures = []
        for name, url, session in pages:
            try:
                status = session.get(url).status_code
            except Exception as exc:  # noqa: BLE001 - report, don't mask
                status = f"{type(exc).__name__}: {exc}"
            ok = status in (200, 302)
            line = f"{str(status):>6}  {name:<24} {url}"
            if ok:
                self.stdout.write(self.style.SUCCESS(f"  ok  {line}"))
            else:
                failures.append((name, url, status))
                self.stdout.write(self.style.ERROR(f"FAIL  {line}"))

        if failures:
            raise CommandError(
                f"{len(failures)} of {len(pages)} pages failed to render."
            )
        self.stdout.write(self.style.SUCCESS(
            f"\nAll {len(pages)} pages rendered."))
