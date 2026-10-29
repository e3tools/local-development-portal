"""
Tests for the category review page (/investments/category-review/), one
section per user story.
"""

import re
from unittest.mock import patch

from django.conf import settings
from django.contrib.admin.sites import site as admin_site
from django.contrib.auth import get_user_model
from django.db import connection
from django.http import QueryDict
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.shortcuts import resolve_url
from django.urls import reverse
from django.utils.html import escape

from administrativelevels.models import AdministrativeLevel, Category, Sector
from investments import category_review as review
from investments.constants import DEFAULT_ESTIMATED_COST, SECTOR_ESTIMATED_COSTS
from investments.models import Investment, InvestmentSectorChange
from investments.views_category_review import PAGE_SIZE

User = get_user_model()

# Two real sector names from the cost table, so the cost rule is exercised.
WATER_SECTOR, CLASSROOM_SECTOR = list(SECTOR_ESTIMATED_COSTS)[:2]


def _user(email, staff=False):
    return User.objects.create_user(
        username=email, email=email, password="testpass123",
        is_approved=True, is_staff=staff,
    )


def _investment(village, sector, title, status=Investment.NOT_FUNDED, cost=5_000_000, **kwargs):
    return Investment.objects.create(
        title=title, description=kwargs.pop("group", "Groupe des femmes"),
        administrative_level=village, sector=sector, estimated_cost=cost,
        duration=30, delays_consumed=0, physical_execution_rate=0,
        financial_implementation_rate=0, investment_status=Investment.PRIORITY,
        project_status=status, no_sql_id="review-%s" % title, **kwargs
    )


class ReviewBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = _user("staff@email.com", staff=True)
        cls.member = _user("member@email.com")
        adm = AdministrativeLevel.objects.create
        commune = adm(name="Parakou", type="commune")
        arrondissement = adm(name="Arr 1", type="arrondissement", parent=commune)
        cls.village = adm(name="Sawararou", type="village", parent=arrondissement)
        cls.water = Category.objects.create(name="Eau")
        cls.education = Category.objects.create(name="Éducation")
        cls.borehole = Sector.objects.create(name=WATER_SECTOR, category=cls.water)
        cls.classroom = Sector.objects.create(name=CLASSROOM_SECTOR, category=cls.education)
        cls.no_cost_sector = Sector.objects.create(name="Sans coût défini", category=cls.education)
        cls.url = reverse("investments:category_review")

    def _login(self, user=None):
        self.client.force_login(user or self.staff)

    def _htmx_get(self, url, **params):
        return self.client.get(url, params, HTTP_HX_REQUEST="true")

    def _htmx_post(self, url, data=None):
        return self.client.post(url, data or {}, HTTP_HX_REQUEST="true")

    def _card_ids(self, response):
        return [int(i) for i in re.findall(r'<article class="review-card[^"]*" id="need-(\d+)"', response.content.decode())]


# ---------------------------------------------------------------------------
# US1 — staff-only access
# ---------------------------------------------------------------------------

class AccessTest(ReviewBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.inv = _investment(cls.village, cls.borehole, "Forage")
        change = InvestmentSectorChange.objects.create(
            investment=cls.inv, old_sector=cls.classroom, new_sector=cls.borehole
        )
        cls.endpoints = [
            ("get", cls.url),
            ("get", reverse("investments:category_review_sector", args=[cls.inv.id])),
            ("post", reverse("investments:category_review_sector", args=[cls.inv.id])),
            ("get", reverse("investments:category_review_history", args=[cls.inv.id])),
            ("post", reverse("investments:category_review_undo", args=[change.id])),
            ("post", reverse("investments:category_review_verify")),
        ]

    def test_anonymous_is_sent_to_login(self):
        for method, url in self.endpoints:
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertTrue(
                response.url.startswith(resolve_url(settings.LOGIN_URL) + "?next="), response.url
            )

    def test_non_staff_gets_404_everywhere(self):
        self._login(self.member)
        for method, url in self.endpoints:
            self.assertEqual(getattr(self.client, method)(url).status_code, 404, url)
        self.inv.refresh_from_db()
        self.assertIsNone(self.inv.category_verified_at)

    def test_staff_gets_the_page(self):
        self._login()
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_sidebar_link_only_for_staff(self):
        home = reverse("investments:home_investments")
        self._login(self.member)
        self.assertNotIn(self.url, self.client.get(home).content.decode())
        self._login()
        self.assertIn(self.url, self.client.get(home).content.decode())


# ---------------------------------------------------------------------------
# US2 — browse investments as cards
# ---------------------------------------------------------------------------

class BrowseTest(ReviewBaseTest):
    def test_card_shows_title_group_location_and_sector(self):
        _investment(self.village, self.borehole, "Réalisation d'un forage", group="Groupe des jeunes")
        self._login()
        html = self.client.get(self.url).content.decode()
        for text in ("Réalisation d'un forage", "Groupe des jeunes", "Sawararou", "Parakou",
                     "Eau", WATER_SECTOR):
            self.assertIn(escape(text), html)

    def test_pagination_and_constant_query_count(self):
        for i in range(PAGE_SIZE + 5):
            _investment(self.village, self.borehole, "Besoin %02d" % i)
        self._login()
        self.client.get(self.url)  # warm session/user lookups
        with CaptureQueriesContext(connection) as page1:
            first = self._htmx_get(self.url)
        with CaptureQueriesContext(connection) as page2:
            second = self._htmx_get(self.url, page=2)
        self.assertEqual(len(self._card_ids(first)), PAGE_SIZE)
        self.assertEqual(len(self._card_ids(second)), 5)
        self.assertEqual(len(page1), len(page2))  # no per-card queries
        self.assertIn("page=2", first.content.decode())

    def test_htmx_request_returns_only_the_results_fragment(self):
        self._login()
        response = self._htmx_get(self.url)
        self.assertTrue(response.content.decode().lstrip().startswith('<div id="review-results">'))
        self.assertNotIn("<html", response.content.decode())


# ---------------------------------------------------------------------------
# US3 — filters
# ---------------------------------------------------------------------------

class FilterTest(ReviewBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.forage = _investment(cls.village, cls.borehole, "Réalisation d'un forage")
        cls.classe = _investment(cls.village, cls.classroom, "Construction de salles de classe")
        cls.forage_in_school = _investment(cls.village, cls.classroom, "Forage pour l'école")
        cls.funded = _investment(
            cls.village, cls.borehole, "Forage financé", status=Investment.FUNDED_NOT_STARTED
        )
        cls.verified = _investment(cls.village, cls.borehole, "Forage déjà vu")
        Investment.objects.filter(pk=cls.verified.pk).update(category_verified_at="2026-10-01T00:00Z")

    def _ids(self, **params):
        self._login()
        return set(self._card_ids(self._htmx_get(self.url, **params)))

    def test_defaults_exclude_funded_and_verified(self):
        self.assertEqual(self._ids(), {self.forage.id, self.classe.id, self.forage_in_school.id})

    def test_category_and_sector(self):
        self.assertEqual(
            self._ids(**{"category-filter": self.water.id}), {self.forage.id}
        )
        self.assertEqual(
            self._ids(**{"sector-filter": [self.classroom.id]}),
            {self.classe.id, self.forage_in_school.id},
        )

    def test_search_in_title_finds_misclassified_needs(self):
        self.assertEqual(self._ids(q="forage"), {self.forage.id, self.forage_in_school.id})
        self.assertEqual(self._ids(q="FORAGE", **{"category-filter": self.education.id}),
                         {self.forage_in_school.id})

    def test_switching_off_exclude_funded_includes_every_funding_state(self):
        # Submitted form with the switch unchecked: the checkbox sends nothing.
        self.assertIn(self.funded.id, self._ids(submitted="1"))
        self.assertNotIn(self.funded.id, self._ids(submitted="1", **{"exclude-funded": "1"}))

    def test_verified_filter(self):
        self.assertEqual(self._ids(verified="done"), {self.verified.id})
        self.assertEqual(
            self._ids(verified="all"),
            {self.forage.id, self.classe.id, self.forage_in_school.id, self.verified.id},
        )
        self.assertEqual(self._ids(verified="bogus"), self._ids())

    def test_progress_counts_ignore_the_verified_filter(self):
        progress = review.ReviewFilters(QueryDict("verified=done")).progress()
        self.assertEqual(progress, {"total": 4, "verified": 1})

    def test_filters_survive_in_pagination_links(self):
        for i in range(PAGE_SIZE):
            _investment(self.village, self.borehole, "Forage %02d" % i)
        self._login()
        html = self._htmx_get(self.url, q="forage", **{"category-filter": self.water.id}).content.decode()
        self.assertRegex(html, r'q=forage[^"]*category-filter=%d[^"]*page=2' % self.water.id)

    def test_page_preselects_the_filters(self):
        self._login()
        html = self.client.get(self.url, {"category-filter": self.water.id, "q": "forage"}).content.decode()
        self.assertRegex(html, r'<option value="%d" selected>Eau</option>' % self.water.id)
        self.assertIn('value="forage"', html)


# ---------------------------------------------------------------------------
# US4 — correct the sub-category of an investment
# ---------------------------------------------------------------------------

class CorrectionTest(ReviewBaseTest):
    def setUp(self):
        self.inv = _investment(self.village, self.borehole, "Salle de classe mal classée", cost=1_234_567)
        self.sector_url = reverse("investments:category_review_sector", args=[self.inv.id])
        self._login()

    def test_form_lists_grouped_sectors_with_current_selected(self):
        html = self._htmx_get(self.sector_url).content.decode()
        self.assertIn('<optgroup label="Éducation">', html)
        self.assertRegex(html, r'<option value="%d" selected>' % self.borehole.id)

    def test_correction_moves_sector_updates_cost_and_marks_verified(self):
        response = self._htmx_post(self.sector_url, {"sector": self.classroom.id})
        self.assertEqual(response.status_code, 200)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.sector, self.classroom)
        self.assertEqual(self.inv.estimated_cost, SECTOR_ESTIMATED_COSTS[CLASSROOM_SECTOR])
        self.assertIsNotNone(self.inv.category_verified_at)
        self.assertEqual(self.inv.category_verified_by, self.staff)

        change = InvestmentSectorChange.objects.get(investment=self.inv)
        self.assertEqual((change.old_sector, change.new_sector), (self.borehole, self.classroom))
        self.assertEqual(change.old_estimated_cost, 1_234_567)
        self.assertEqual(change.changed_by, self.staff)

        html = response.content.decode()
        self.assertIn("is-moved", html)
        self.assertIn(reverse("investments:category_review_undo", args=[change.id]), html)

    def test_sector_without_cost_uses_the_default_cost(self):
        self._htmx_post(self.sector_url, {"sector": self.no_cost_sector.id})
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.estimated_cost, DEFAULT_ESTIMATED_COST)

    def test_same_sector_only_marks_verified(self):
        self._htmx_post(self.sector_url, {"sector": self.borehole.id})
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.estimated_cost, 1_234_567)
        self.assertIsNotNone(self.inv.category_verified_at)
        self.assertFalse(InvestmentSectorChange.objects.exists())

    def test_invalid_sector_is_rejected(self):
        for value in ("", "abc", "999999"):
            self.assertEqual(self._htmx_post(self.sector_url, {"sector": value}).status_code, 400)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.sector, self.borehole)

    def test_funded_investments_can_be_corrected(self):
        Investment.objects.filter(pk=self.inv.pk).update(project_status=Investment.COMPLETED)
        self._htmx_post(self.sector_url, {"sector": self.classroom.id})
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.sector, self.classroom)


# ---------------------------------------------------------------------------
# US5 — history and undo
# ---------------------------------------------------------------------------

class HistoryUndoTest(ReviewBaseTest):
    def setUp(self):
        self.inv = _investment(self.village, self.borehole, "Besoin", cost=7_777_777)
        self._login()
        self._htmx_post(
            reverse("investments:category_review_sector", args=[self.inv.id]),
            {"sector": self.classroom.id},
        )
        self.change = InvestmentSectorChange.objects.get()
        self.undo_url = reverse("investments:category_review_undo", args=[self.change.id])

    def test_undo_restores_the_exact_previous_sector_and_cost(self):
        response = self._htmx_post(self.undo_url)
        self.assertEqual(response.status_code, 200)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.sector, self.borehole)
        self.assertEqual(self.inv.estimated_cost, 7_777_777)  # not the table cost
        undo = InvestmentSectorChange.objects.exclude(pk=self.change.pk).get()
        self.assertEqual(undo.undoes, self.change)
        self.assertEqual((undo.old_sector, undo.new_sector), (self.classroom, self.borehole))

    def test_undo_twice_is_refused(self):
        self._htmx_post(self.undo_url)
        response = self._htmx_post(self.undo_url)
        self.assertIn("ne peut plus être annulée", response.content.decode())
        self.assertEqual(InvestmentSectorChange.objects.count(), 2)

    def test_undo_after_a_later_correction_is_refused(self):
        self._htmx_post(
            reverse("investments:category_review_sector", args=[self.inv.id]),
            {"sector": self.no_cost_sector.id},
        )
        self._htmx_post(self.undo_url)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.sector, self.no_cost_sector)

    def test_history_lists_every_change(self):
        self._htmx_post(self.undo_url)
        html = self._htmx_get(
            reverse("investments:category_review_history", args=[self.inv.id])
        ).content.decode()
        self.assertEqual(html.count("<li>"), 2)
        self.assertIn("annulation", html)
        self.assertIn("staff@email.com", html)

    def test_card_offers_history_only_when_there_is_some(self):
        other = _investment(self.village, self.borehole, "Jamais corrigé")
        html = self._htmx_get(self.url, verified="all").content.decode()
        self.assertIn(reverse("investments:category_review_history", args=[self.inv.id]), html)
        self.assertNotIn(reverse("investments:category_review_history", args=[other.id]), html)

    def test_admin_log_is_read_only(self):
        model_admin = admin_site._registry[InvestmentSectorChange]
        request = RequestFactory().get("/")
        request.user = self.staff
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, self.change))
        self.assertFalse(model_admin.has_delete_permission(request, self.change))


# ---------------------------------------------------------------------------
# US6 — validate the page, progress
# ---------------------------------------------------------------------------

class VerifyPageTest(ReviewBaseTest):
    def test_validate_marks_shown_investments_and_refreshes_results(self):
        shown = [_investment(self.village, self.borehole, "A%d" % i) for i in range(3)]
        untouched = _investment(self.village, self.classroom, "Autre catégorie")
        self._login()
        verify_url = reverse("investments:category_review_verify") + "?category-filter=%d" % self.water.id
        response = self._htmx_post(verify_url, {"investment": [i.id for i in shown]})

        self.assertEqual(
            Investment.objects.filter(category_verified_at__isnull=False).count(), 3
        )
        untouched.refresh_from_db()
        self.assertIsNone(untouched.category_verified_at)
        html = response.content.decode()
        self.assertTrue(html.lstrip().startswith('<div id="review-results">'))
        # Same filters, "to verify" by default: the validated ones are gone.
        self.assertEqual(self._card_ids(response), [])
        self.assertIn("3 / 3", html)

    def test_validate_keeps_the_first_verifier(self):
        inv = _investment(self.village, self.borehole, "Déjà vérifié")
        Investment.objects.filter(pk=inv.pk).update(
            category_verified_at="2026-10-01T00:00Z", category_verified_by=self.member
        )
        self._login()
        self._htmx_post(reverse("investments:category_review_verify"), {"investment": [inv.id]})
        inv.refresh_from_db()
        self.assertEqual(inv.category_verified_by, self.member)

    def test_validate_button_lists_only_unverified_cards(self):
        todo = _investment(self.village, self.borehole, "À voir")
        done = _investment(self.village, self.borehole, "Vu")
        Investment.objects.filter(pk=done.pk).update(category_verified_at="2026-10-01T00:00Z")
        self._login()
        html = self._htmx_get(self.url, verified="all").content.decode()
        self.assertIn('name="investment" value="%d"' % todo.id, html)
        self.assertNotIn('name="investment" value="%d"' % done.id, html)


class PageViewTrackingTest(ReviewBaseTest):
    def test_htmx_fragments_are_not_tracked_as_page_views(self):
        self._login()
        with patch("cosomis.mixins.track_user_activity") as track:
            self._htmx_get(self.url)
            track.assert_not_called()
            self.client.get(self.url)
            track.assert_called_once()
