from unittest.mock import patch, MagicMock

from django.test import TestCase

from administrativelevels.models import AdministrativeLevel
from administrativelevels.services.canton_summary_service import CantonSummaryService


class CantonSummaryServicePopulationTest(TestCase):

    def _make_canton(self):
        canton = MagicMock(spec=AdministrativeLevel)
        canton.type = AdministrativeLevel.CANTON
        canton.id = 1
        return canton

    @patch('administrativelevels.services.canton_summary_service.AdministrativeLevel.objects')
    def test_population_aggregates_sums_child_villages(self, mock_adm_objects):
        """Service must return summed demographics, not canton-level values."""
        mock_qs = MagicMock()
        mock_adm_objects.filter.return_value = mock_qs
        mock_qs.aggregate.return_value = {
            'total': 1500, 'men': 700, 'women': 800,
            'young': 400, 'elder': 200, 'disabilities': 50,
            'agriculturists': 300, 'pastoralists': 150, 'minorities': 100,
        }
        mock_qs.exclude.return_value = mock_qs
        mock_qs.values_list.return_value = ['Bariba', 'Peulh']

        service = CantonSummaryService.__new__(CantonSummaryService)
        service._canton = self._make_canton()
        service._child_villages = mock_qs

        result = service.get_population_aggregates()

        self.assertEqual(result['total'], 1500)
        self.assertEqual(result['men'], 700)
        self.assertIn('ethnic_groups', result)

    @patch('administrativelevels.services.canton_summary_service.AdministrativeLevel.objects')
    def test_population_aggregates_with_zero_villages(self, mock_adm_objects):
        """With no child villages all counts should be 0."""
        mock_qs = MagicMock()
        mock_adm_objects.filter.return_value = mock_qs
        mock_qs.aggregate.return_value = {
            'total': 0, 'men': 0, 'women': 0, 'young': 0,
            'elder': 0, 'disabilities': 0, 'agriculturists': 0,
            'pastoralists': 0, 'minorities': 0,
        }
        mock_qs.exclude.return_value = mock_qs
        mock_qs.values_list.return_value = []

        service = CantonSummaryService.__new__(CantonSummaryService)
        service._canton = self._make_canton()
        service._child_villages = mock_qs

        result = service.get_population_aggregates()

        self.assertEqual(result['total'], 0)
        self.assertEqual(result['ethnic_groups'], '')

    @patch('administrativelevels.services.canton_summary_service.AdministrativeLevel.objects')
    def test_ethnic_groups_deduplicates_across_villages(self, mock_adm_objects):
        """Bariba appearing in 3 villages must appear only once in the label."""
        mock_qs = MagicMock()
        mock_adm_objects.filter.return_value = mock_qs
        mock_qs.aggregate.return_value = {k: 0 for k in [
            'total', 'men', 'women', 'young', 'elder',
            'disabilities', 'agriculturists', 'pastoralists', 'minorities'
        ]}
        mock_qs.exclude.return_value = mock_qs
        # Two villages: "Bariba, Peulh" and "Bariba, Dendi"
        mock_qs.values_list.return_value = ['Bariba, Peulh', 'Bariba, Dendi']

        service = CantonSummaryService.__new__(CantonSummaryService)
        service._canton = self._make_canton()
        service._child_villages = mock_qs

        result = service.get_population_aggregates()
        groups = [g.strip() for g in result['ethnic_groups'].split(',')]

        self.assertEqual(groups.count('Bariba'), 1)
        self.assertIn('Peulh', groups)
        self.assertIn('Dendi', groups)


class CantonSummaryServiceVillagesSummaryTest(TestCase):

    @patch('administrativelevels.services.canton_summary_service.Investment.objects')
    @patch('administrativelevels.services.canton_summary_service.AdministrativeLevel.objects')
    def test_villages_summary_returns_correct_counts(self, mock_adm, mock_inv):
        """villages_summary must return village_count, cvd_count,
        priority_count and total_estimated_cost."""
        mock_village_qs = MagicMock()
        mock_village_qs.count.return_value = 8
        mock_village_qs.values_list.return_value = [1, 2, 3]
        mock_village_qs.filter.return_value = mock_village_qs
        mock_village_qs.values.return_value = mock_village_qs
        mock_village_qs.distinct.return_value = mock_village_qs

        mock_inv_qs = MagicMock()
        mock_inv.filter.return_value = mock_inv_qs
        mock_inv_qs.aggregate.return_value = {
            'priority_count': 23,
            'total_estimated_cost': 245_000_000,
        }

        canton = MagicMock(spec=AdministrativeLevel)
        canton.type = AdministrativeLevel.CANTON

        service = CantonSummaryService.__new__(CantonSummaryService)
        service._canton = canton
        service._child_villages = mock_village_qs

        result = service.get_villages_summary()

        self.assertEqual(result['village_count'], 8)
        self.assertEqual(result['priority_count'], 23)
        self.assertEqual(result['total_estimated_cost'], 245_000_000)


class CantonSummaryServiceCarouselTest(TestCase):

    @patch('administrativelevels.services.canton_summary_service.Attachment.objects')
    @patch('administrativelevels.services.canton_summary_service.AdministrativeLevel.objects')
    def test_carousel_returns_empty_list_when_no_attachments(self, mock_adm, mock_att):
        """When no images exist, carousel returns []; template shows default."""
        mock_att_qs = MagicMock()
        mock_att.objects.filter.return_value = mock_att_qs
        mock_att_qs.filter.return_value = mock_att_qs
        mock_att_qs.__iter__ = lambda s: iter([])
        mock_att_qs.__len__ = lambda s: 0
        # Simulate slicing returning empty list
        mock_att_qs.__getitem__ = lambda s, k: []

        canton = MagicMock(spec=AdministrativeLevel)
        canton.type = AdministrativeLevel.CANTON

        service = CantonSummaryService.__new__(CantonSummaryService)
        service._canton = canton
        service._child_villages = MagicMock()

        result = service.get_carousel_images()
        self.assertIsInstance(result, list)
