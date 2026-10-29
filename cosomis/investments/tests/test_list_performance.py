"""
Query-count / payload guards for the /investments/ page and its AJAX calls,
so the optimisations don't silently regress.
"""

from django.db import connection
from django.test.utils import CaptureQueriesContext

from administrativelevels.models import AdministrativeLevel
from investments.models import Investment
from investments.tests.test_list_filters import FiltersBaseTest, _make_investment

DATATABLE_COLUMNS = (
    "select_input", "title",
    "administrative_level__type_with_projects_priority_came_from",
    "estimated_cost", "administrative_level__name",
    "administrative_level__parent__name",
    "administrative_level__parent__parent__name",
    "administrative_level__parent__parent__parent__name",
    "ranking", "population_priority",
)


def _datatable_querystring(length=10):
    """What the browser's DataTable sends: draw/paging/order plus columns."""
    params = ["format=datatables", "draw=1", "start=0", "length=%d" % length,
              "order[0][column]=3", "order[0][dir]=asc"]
    for i, column in enumerate(DATATABLE_COLUMNS):
        params.append("columns[%d][data]=%s" % (i, column))
        params.append("columns[%d][orderable]=true" % i)
    return "&".join(params)


class DatatablePerformanceTest(FiltersBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        adm = AdministrativeLevel.objects.create
        commune = adm(name="Commune P", type="commune")
        canton = adm(name="Arr P", type="arrondissement", parent=commune)
        cls.villages = [
            adm(name="Village P%d" % i, type="village", parent=canton) for i in range(3)
        ]
        cls.datatable_url = cls.url + "ajax/datatable/?" + _datatable_querystring()

    def _add_investments(self, count):
        start = Investment.objects.count()
        for i in range(count):
            _make_investment(self.villages[i % 3], self.sector, "perf-%d" % (start + i))

    def _get_datatable(self):
        self._login()
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(self.datatable_url)
        self.assertEqual(response.status_code, 200)
        return response, ctx

    def test_query_count_does_not_grow_with_rows(self):
        self._add_investments(2)
        _, few = self._get_datatable()
        self._add_investments(8)
        response, many = self._get_datatable()
        self.assertEqual(len(response.json()["data"]), 10)
        self.assertEqual(len(few), len(many))

    def test_unused_columns_are_not_loaded(self):
        self._add_investments(1)
        _, ctx = self._get_datatable()
        select = next(
            q["sql"] for q in ctx.captured_queries
            if q["sql"].startswith('SELECT "investments_investment"."id"')
        )
        for column in ("abandonment_history", "climate_contribution_text", "no_sql_id"):
            self.assertNotIn(column, select)
        # and no column of the joined admin levels besides the four we render
        self.assertNotIn("total_population", select)

    def test_rows_only_carry_datatable_columns(self):
        self._add_investments(1)
        response, _ = self._get_datatable()
        row = response.json()["data"][0]
        self.assertEqual(
            set(row) - {"DT_RowId", "DT_RowAttr"}, set(DATATABLE_COLUMNS)
        )


class TotalsPerformanceTest(FiltersBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        other = AdministrativeLevel.objects.create(name="Village B", type=AdministrativeLevel.VILLAGE)
        _make_investment(cls.village, cls.sector, "t1")
        _make_investment(cls.village, cls.sector, "t2")
        _make_investment(other, cls.sector, "t3")
        cls.totals_url = cls.url + "ajax/datatable/total-results/"

    def test_totals_are_computed_in_one_query(self):
        self._login()
        self.client.get(self.url)  # warm the session/user lookups out of the count
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.post(
                self.totals_url,
                {"all_queryset": "false", "selected_ids": "", "project_id": ""},
            )
        self.assertEqual(response.status_code, 200)
        investment_queries = [
            q for q in ctx.captured_queries if "investments_investment" in q["sql"]
        ]
        self.assertEqual(len(investment_queries), 1)
        self.assertEqual(response.json()["total_subprojects_display"], 3)
        self.assertEqual(response.json()["total_villages_display"], 2)
        self.assertEqual(response.json()["total_funding_display"], 3_000_000)


class AdmDropdownsRenderingTest(FiltersBaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        adm = AdministrativeLevel.objects.create
        cls.country = adm(name="Pays", type="country")
        cls.dept = adm(name="Dept", type="département", parent=cls.country)
        cls.commune = adm(name="Commune", type="commune", parent=cls.dept)

    def test_dropdowns_without_selected_parent_are_empty(self):
        self._login()
        ctx = self.client.get(self.url).context
        # Single root: the prefecture dropdown is pre-loaded from it...
        self.assertEqual(list(ctx["prefectures"]), [self.dept])
        # ...but nothing below it is rendered until a parent is picked.
        self.assertEqual(list(ctx["communes"]), [])
        self.assertEqual(list(ctx["cantons"]), [])
        self.assertEqual(list(ctx["villages"]), [])
