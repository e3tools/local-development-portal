"""
Tests for the multi-select filters on /investments/ (IndexListView +
InvestmentModelViewSet.get_queryset).
"""

import re

from django.contrib.auth import get_user_model
from django.http import QueryDict
from django.test import TestCase
from django.urls import reverse
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from administrativelevels.models import AdministrativeLevel, Category, Sector
from administrativelevels.templatetags.custom_tags import getlist, getlist_int
from investments.ajax_views import InvestmentModelViewSet
from investments.models import Investment
from investments.views import IndexListView

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username="officer_filters@email.com"):
    return User.objects.create_user(
        username=username,
        email=username,
        password="testpass123",
        is_approved=True,
    )


def _make_investment(adm, sector, title, status=Investment.NOT_FUNDED, **kwargs):
    return Investment.objects.create(
        title=title,
        administrative_level=adm,
        sector=sector,
        estimated_cost=1_000_000,
        duration=30,
        delays_consumed=0,
        physical_execution_rate=0,
        financial_implementation_rate=0,
        investment_status=Investment.PRIORITY,
        project_status=status,
        no_sql_id=f"test-id-{title}",
        **kwargs
    )


def _filtered_queryset(params):
    """Run InvestmentModelViewSet.get_queryset() against a GET querystring.
    List values in `params` are sent as repeated keys (?k=a&k=b)."""
    view = InvestmentModelViewSet()
    view.request = Request(APIRequestFactory().get("/", params))
    view.format_kwarg = None
    return view.get_queryset()


def _filtered_ids(params):
    return set(_filtered_queryset(params).values_list("id", flat=True))


def _subpopulation_name(field):
    return str(next(
        sp["name"] for sp in IndexListView.SUBPOPULATIONS if sp["id"] == field
    ))


def _selected_values(html, select_name):
    """Values of the <option selected> inside <select name=select_name>
    (label-agnostic, so tests don't depend on the active translation)."""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)  # list.html keeps old selects commented out
    select = re.search(
        r'<select[^>]*name="%s"[^>]*>(.*?)</select>' % re.escape(select_name),
        html, re.S,
    )
    assert select, "select %s not rendered" % select_name
    return re.findall(r'<option value="([^"]*)"[^>]*\bselected\b', select.group(1))


class FiltersBaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user()
        cls.village = AdministrativeLevel.objects.create(
            name="Village A", type=AdministrativeLevel.VILLAGE
        )
        cls.category = Category.objects.create(name="Infrastructure")
        cls.sector = Sector.objects.create(name="Water", category=cls.category)
        cls.url = reverse("investments:home_investments")

    def _login(self):
        self.client.force_login(self.user)


# ---------------------------------------------------------------------------
# Template filters
# ---------------------------------------------------------------------------

class GetlistTemplateFilterTest(TestCase):
    def test_getlist_skips_blanks(self):
        qd = QueryDict("k=a&k=&k=b")
        self.assertEqual(getlist(qd, "k"), ["a", "b"])

    def test_getlist_on_non_querydict_returns_empty(self):
        self.assertEqual(getlist({"k": "a"}, "k"), [])

    def test_getlist_int_skips_non_numeric(self):
        qd = QueryDict("k=1&k=x&k=&k=3")
        self.assertEqual(getlist_int(qd, "k"), [1, 3])


# ---------------------------------------------------------------------------
# Funding status (is-funded-filter)
# ---------------------------------------------------------------------------

class FundingStatusFilterTest(FiltersBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.not_funded = _make_investment(
            cls.village, cls.sector, "not-funded", status=Investment.NOT_FUNDED
        )
        cls.in_progress = _make_investment(
            cls.village, cls.sector, "in-progress", status=Investment.IN_PROGRESS
        )
        cls.completed = _make_investment(
            cls.village, cls.sector, "completed", status=Investment.COMPLETED
        )

    def test_no_filter_returns_all(self):
        self.assertEqual(
            _filtered_ids({}),
            {self.not_funded.id, self.in_progress.id, self.completed.id},
        )

    def test_single_value(self):
        self.assertEqual(
            _filtered_ids({"is-funded-filter": "in_progress"}),
            {self.in_progress.id},
        )

    def test_multiple_values_are_ored(self):
        self.assertEqual(
            _filtered_ids({"is-funded-filter": ["not_funded", "completed"]}),
            {self.not_funded.id, self.completed.id},
        )

    def test_blank_and_unknown_values_are_ignored(self):
        self.assertEqual(
            _filtered_ids({"is-funded-filter": ["", "bogus"]}),
            {self.not_funded.id, self.in_progress.id, self.completed.id},
        )
        self.assertEqual(
            _filtered_ids({"is-funded-filter": ["", "bogus", "completed"]}),
            {self.completed.id},
        )

    def test_selected_options_are_preselected_in_template(self):
        self._login()
        response = self.client.get(
            self.url + "?is-funded-filter=not_funded&is-funded-filter=completed"
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(
            _selected_values(html, "is-funded-filter"), ["not_funded", "completed"]
        )


# ---------------------------------------------------------------------------
# Endorsed by (subpopulation-filter)
# ---------------------------------------------------------------------------

class SubpopulationFilterTest(FiltersBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.youth = _make_investment(
            cls.village, cls.sector, "youth", endorsed_by_youth=True
        )
        cls.chiefs = _make_investment(
            cls.village, cls.sector, "chiefs", endorsed_by_chiefs=True
        )
        cls.women = _make_investment(
            cls.village, cls.sector, "women", endorsed_by_women=True
        )
        # Not the case in the BJ data today, but the filter must stay correct
        # if a need ever gets endorsed by several groups.
        cls.youth_and_women = _make_investment(
            cls.village, cls.sector, "youth-women",
            endorsed_by_youth=True, endorsed_by_women=True,
        )
        cls.nobody = _make_investment(cls.village, cls.sector, "nobody")

    def test_no_filter_returns_all(self):
        self.assertEqual(len(_filtered_ids({})), 5)

    def test_single_group(self):
        self.assertEqual(
            _filtered_ids({"subpopulation-filter": "endorsed_by_chiefs"}),
            {self.chiefs.id},
        )

    def test_multiple_groups_are_ored(self):
        self.assertEqual(
            _filtered_ids(
                {"subpopulation-filter": ["endorsed_by_youth", "endorsed_by_chiefs"]}
            ),
            {self.youth.id, self.chiefs.id, self.youth_and_women.id},
        )

    def test_need_endorsed_by_several_selected_groups_is_returned_once(self):
        qs = _filtered_queryset(
            {"subpopulation-filter": ["endorsed_by_youth", "endorsed_by_women"]}
        )
        self.assertEqual(qs.count(), 3)

    def test_blank_and_non_whitelisted_values_are_ignored(self):
        # Anything outside the whitelist used to be passed straight to
        # .filter(**{value: True}); it must now be ignored.
        self.assertEqual(
            len(_filtered_ids({"subpopulation-filter": ["", "climate_contribution", "id"]})),
            5,
        )
        self.assertEqual(
            _filtered_ids(
                {"subpopulation-filter": ["climate_contribution", "endorsed_by_women"]}
            ),
            {self.women.id, self.youth_and_women.id},
        )

    def test_whitelist_matches_the_options_shown_in_the_page(self):
        self.assertEqual(
            [sp["id"] for sp in IndexListView.SUBPOPULATIONS],
            list(InvestmentModelViewSet.SUBPOPULATION_FILTER_FIELDS),
        )

    def test_selected_options_are_preselected_in_template(self):
        self._login()
        response = self.client.get(
            self.url
            + "?subpopulation-filter=endorsed_by_youth"
            + "&subpopulation-filter=endorsed_by_chiefs"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            _selected_values(response.content.decode(), "subpopulation-filter"),
            ["endorsed_by_youth", "endorsed_by_chiefs"],
        )

    def test_unknown_value_does_not_crash_the_page(self):
        # IndexListView.get_queryset() used to call .filter(**{value: True})
        # with the raw value, raising FieldError (HTTP 500).
        self._login()
        response = self.client.get(self.url + "?subpopulation-filter=bogus")
        self.assertEqual(response.status_code, 200)

    def test_badge_lists_every_selected_group(self):
        self._login()
        response = self.client.get(
            self.url
            + "?subpopulation-filter=endorsed_by_youth"
            + "&subpopulation-filter=endorsed_by_chiefs"
            + "&subpopulation-filter=bogus"
        )
        badges = response.context["query_strings"]
        self.assertEqual(
            badges["Subpopulations"],
            "%s, %s" % (_subpopulation_name("endorsed_by_youth"),
                        _subpopulation_name("endorsed_by_chiefs")),
        )


# ---------------------------------------------------------------------------
# Administrative levels (prefecture/commune/canton/village-filter)
# ---------------------------------------------------------------------------

class AdmLevelFilterTest(FiltersBaseTest):
    """Uses the Benin vocabulary (country/département/arrondissement) so the
    type-alias handling is exercised, not just the Togo canonical names."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        adm = AdministrativeLevel.objects.create
        cls.country = adm(name="Bénin", type="country")
        cls.d1 = adm(name="Dept 1", type="département", parent=cls.country)
        cls.d2 = adm(name="Dept 2", type="département", parent=cls.country)
        cls.c1 = adm(name="Commune 1", type="commune", parent=cls.d1)
        cls.c2 = adm(name="Commune 2", type="commune", parent=cls.d1)
        cls.c3 = adm(name="Commune 3", type="commune", parent=cls.d2)
        cls.a1 = adm(name="Arr 1", type="arrondissement", parent=cls.c1)
        cls.a2 = adm(name="Arr 2", type="arrondissement", parent=cls.c2)
        cls.a3 = adm(name="Arr 3", type="arrondissement", parent=cls.c3)
        cls.v1 = adm(name="Village 1", type="village", parent=cls.a1)
        cls.v1b = adm(name="Village 1b", type="village", parent=cls.a1)
        cls.v2 = adm(name="Village 2", type="village", parent=cls.a2)
        cls.v3 = adm(name="Village 3", type="village", parent=cls.a3)
        cls.i1 = _make_investment(cls.v1, cls.sector, "v1")
        cls.i1b = _make_investment(cls.v1b, cls.sector, "v1b")
        cls.i2 = _make_investment(cls.v2, cls.sector, "v2")
        cls.i3 = _make_investment(cls.v3, cls.sector, "v3")
        cls.all_bj = {cls.i1.id, cls.i1b.id, cls.i2.id, cls.i3.id}

    # --- InvestmentModelViewSet.get_queryset() ----------------------------

    def test_multiple_prefectures(self):
        self.assertEqual(
            _filtered_ids({"prefecture-filter": [self.d1.id, self.d2.id]}), self.all_bj
        )
        self.assertEqual(
            _filtered_ids({"prefecture-filter": [self.d1.id]}),
            {self.i1.id, self.i1b.id, self.i2.id},
        )

    def test_multiple_communes(self):
        self.assertEqual(
            _filtered_ids({"commune-filter": [self.c1.id, self.c3.id]}),
            {self.i1.id, self.i1b.id, self.i3.id},
        )

    def test_multiple_cantons(self):
        self.assertEqual(
            _filtered_ids({"canton-filter": [self.a2.id, self.a3.id]}),
            {self.i2.id, self.i3.id},
        )

    def test_multiple_villages(self):
        self.assertEqual(
            _filtered_ids({"village-filter": [self.v1.id, self.v3.id]}),
            {self.i1.id, self.i3.id},
        )

    def test_levels_are_anded(self):
        # Selecting a commune narrows the selected departments down to it.
        self.assertEqual(
            _filtered_ids({
                "prefecture-filter": [self.d1.id, self.d2.id],
                "commune-filter": [self.c1.id],
            }),
            {self.i1.id, self.i1b.id},
        )

    def test_blank_and_non_numeric_ids_are_ignored(self):
        self.assertEqual(
            _filtered_ids({"commune-filter": ["", "abc", self.c3.id]}), {self.i3.id}
        )
        self.assertIn(self.i1.id, _filtered_ids({"commune-filter": ["", "abc"]}))

    # --- FillAdmLevelsSelectFilters (cascade endpoint) --------------------

    def _children(self, values):
        self._login()
        response = self.client.post(self.url + "ajax/adm-levels", {"value": values})
        self.assertEqual(response.status_code, 200)
        return {v["id"] for v in response.json()["values"]}

    def test_endpoint_returns_children_of_every_selected_parent(self):
        self.assertEqual(
            self._children([self.d1.id, self.d2.id]),
            {self.c1.id, self.c2.id, self.c3.id},
        )
        self.assertEqual(
            self._children([self.c1.id, self.c3.id]), {self.a1.id, self.a3.id}
        )
        self.assertEqual(
            self._children([self.a1.id, self.a2.id]),
            {self.v1.id, self.v1b.id, self.v2.id},
        )

    def test_endpoint_single_parent_still_works(self):
        self.assertEqual(self._children([self.country.id]), {self.d1.id, self.d2.id})

    def test_endpoint_without_valid_parent_returns_nothing(self):
        self.assertEqual(self._children([""]), set())
        self.assertEqual(self._children(["abc"]), set())

    # --- IndexListView context / template ---------------------------------

    def _get_page(self, querystring):
        self._login()
        response = self.client.get(self.url + querystring)
        self.assertEqual(response.status_code, 200)
        return response

    def test_dropdowns_list_children_of_every_selected_parent(self):
        response = self._get_page(
            "?prefecture-filter=%d&prefecture-filter=%d"
            "&commune-filter=%d&commune-filter=%d&canton-filter=%d"
            % (self.d1.id, self.d2.id, self.c1.id, self.c3.id, self.a1.id)
        )
        ctx = response.context
        self.assertEqual(
            set(ctx["communes"]), {self.c1, self.c2, self.c3}
        )
        self.assertEqual(set(ctx["cantons"]), {self.a1, self.a3})
        # Used to read the misspelt "cantons-filter" and list every village.
        self.assertEqual(set(ctx["villages"]), {self.v1, self.v1b})

    def test_selected_options_are_preselected_in_template(self):
        response = self._get_page(
            "?prefecture-filter=%d&prefecture-filter=%d"
            "&commune-filter=%d&commune-filter=%d"
            "&canton-filter=%d&village-filter=%d&village-filter=%d"
            % (self.d1.id, self.d2.id, self.c1.id, self.c3.id,
               self.a1.id, self.v1.id, self.v1b.id)
        )
        html = response.content.decode()
        self.assertEqual(
            _selected_values(html, "prefecture-filter"), [str(self.d1.id), str(self.d2.id)]
        )
        self.assertEqual(
            set(_selected_values(html, "commune-filter")), {str(self.c1.id), str(self.c3.id)}
        )
        self.assertEqual(_selected_values(html, "canton-filter"), [str(self.a1.id)])
        self.assertEqual(
            set(_selected_values(html, "village-filter")), {str(self.v1.id), str(self.v1b.id)}
        )

    def test_badges_list_every_selected_value(self):
        other_category = Category.objects.create(name="Health")
        other_sector = Sector.objects.create(name="Clinic", category=other_category)
        response = self._get_page(
            "?commune-filter=%d&commune-filter=%d&canton-filter=%d"
            "&category-filter=%d&category-filter=%d"
            "&sector-filter=%d&sector-filter=%d"
            % (self.c1.id, self.c3.id, self.a2.id,
               self.category.id, other_category.id,
               self.sector.id, other_sector.id)
        )
        badges = response.context["query_strings"]
        split = lambda value: set(value.split(", "))
        self.assertEqual(split(badges["Communes"]), {"Commune 1", "Commune 3"})
        self.assertEqual(badges["Cantons"], "Arr 2")
        self.assertEqual(split(badges["Categories"]), {"Infrastructure", "Health"})
        self.assertEqual(split(badges["Sectors"]), {"Water", "Clinic"})

    def test_single_root_badge_is_hidden(self):
        badges = self._get_page("?region-filter=%d" % self.country.id).context["query_strings"]
        self.assertNotIn("Regions", badges)

    def test_root_badge_is_shown_when_there_are_several_roots(self):
        AdministrativeLevel.objects.create(name="Togo", type="Region")
        badges = self._get_page("?region-filter=%d" % self.country.id).context["query_strings"]
        self.assertEqual(badges["Regions"], "Bénin")

    def test_post_keeps_every_selected_commune(self):
        self._login()
        response = self.client.post(
            self.url, {"commune-filter": ["", self.c1.id, self.c3.id]}
        )
        _, _, query = response.url.partition("?")
        self.assertEqual(
            QueryDict(query).getlist("commune-filter"), [str(self.c1.id), str(self.c3.id)]
        )


# ---------------------------------------------------------------------------
# IndexListView.post() querystring merge
# ---------------------------------------------------------------------------

class FilterFormPostTest(FiltersBaseTest):
    def _post(self, querystring, data):
        self._login()
        return self.client.post(self.url + querystring, data)

    def _redirect_query(self, response):
        self.assertEqual(response.status_code, 302)
        _, _, query = response.url.partition("?")
        return QueryDict(query)

    def test_multiple_funding_values_are_kept(self):
        response = self._post("", {"is-funded-filter": ["", "not_funded", "completed"]})
        self.assertEqual(
            self._redirect_query(response).getlist("is-funded-filter"),
            ["not_funded", "completed"],
        )

    def test_new_selection_replaces_previous_one(self):
        response = self._post(
            "?is-funded-filter=completed",
            {"is-funded-filter": ["", "in_progress"]},
        )
        self.assertEqual(
            self._redirect_query(response).getlist("is-funded-filter"),
            ["in_progress"],
        )

    def test_clearing_every_option_removes_the_filter(self):
        # A <select multiple> with nothing selected submits nothing; the hidden
        # empty input in the template is what makes the key arrive here.
        response = self._post(
            "?is-funded-filter=completed&category-filter=%d" % self.category.id,
            {"is-funded-filter": [""], "category-filter": [""], "sector-filter": [""]},
        )
        query = self._redirect_query(response)
        self.assertNotIn("is-funded-filter", query)
        self.assertNotIn("category-filter", query)

    def test_filters_from_other_forms_are_preserved(self):
        response = self._post(
            "?village-filter=%d" % self.village.id,
            {"is-funded-filter": ["", "completed"]},
        )
        query = self._redirect_query(response)
        self.assertEqual(query.getlist("village-filter"), [str(self.village.id)])
        self.assertEqual(query.getlist("is-funded-filter"), ["completed"])

    def test_template_always_submits_multiselect_keys(self):
        self._login()
        html = self.client.get(self.url).content.decode()
        for name in (
            "category-filter", "sector-filter",
            "is-funded-filter", "subpopulation-filter",
            "prefecture-filter", "commune-filter", "canton-filter", "village-filter",
        ):
            self.assertInHTML(
                '<input type="hidden" name="%s" value="">' % name, html
            )
