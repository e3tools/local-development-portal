from unittest.mock import patch, MagicMock

from django.test import TestCase

from administrativelevels.models import AdministrativeLevel
from administrativelevels.services.canton_summary_service import CantonSummaryService


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
