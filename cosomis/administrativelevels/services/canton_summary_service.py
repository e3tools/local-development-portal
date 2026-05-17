from django.db.models import Sum, Count, Q
from django.db.models.functions import Coalesce
from cosomis.constants import IMAGE_EXTENSIONS
from administrativelevels.models import AdministrativeLevel
from investments.models import Attachment, Investment


class CantonSummaryService:
    """
    Aggregation service for the Canton Profile overview cards.
    Single Responsibility: compute the data for Population card,
    Villages Summary card, and Carousel images.
    All DB queries live here — never in views or templates.
    """

    def __init__(self, canton: AdministrativeLevel):
        assert canton.is_canton(), (
            f"Expected canton-type AdministrativeLevel, got type={canton.type!r}"
        )
        self._canton = canton
        self._child_villages = AdministrativeLevel.objects.filter(
            parent=canton,
        ).filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE),
        )

    def get_population_aggregates(self) -> dict:
        """
        Returns summed demographics from all child villages.
        """
        return self._child_villages.aggregate(
            total=Coalesce(Sum('total_population'), 0),
            men=Coalesce(Sum('population_men'), 0),
            women=Coalesce(Sum('population_women'), 0),
            young=Coalesce(Sum('population_young'), 0),
            elder=Coalesce(Sum('population_elder'), 0),
            disabilities=Coalesce(Sum('population_handicap'), 0),
            agriculturists=Coalesce(Sum('population_agriculturist'), 0),
            pastoralists=Coalesce(Sum('population_pastoralist'), 0),
            minorities=Coalesce(Sum('population_minorities'), 0),
        )

    def get_villages_summary(self) -> dict:
        """
        Returns quick stats for the Villages Summary card:
        village_count, cvd_count, priority_count, total_estimated_cost.
        """
        village_ids = self._child_villages.values_list('id', flat=True)

        investment_agg = Investment.objects.filter(
            administrative_level__in=village_ids
        ).aggregate(
            priority_count=Count('id'),
            total_estimated_cost=Coalesce(Sum('estimated_cost'), 0),
        )

        # CVD count: geographical units linked to child villages
        cvd_count = (
            self._child_villages
            .filter(geographical_unit__isnull=False)
            .values('geographical_unit')
            .distinct()
            .count()
        )

        return {
            'village_count': self._child_villages.count(),
            'cvd_count': cvd_count,
            'priority_count': investment_agg['priority_count'],
            'total_estimated_cost': investment_agg['total_estimated_cost'],
        }

    def get_carousel_images(self, max_images: int = 5) -> list:
        """
        Returns up to max_images Attachment instances from child villages,
        prioritizing COMPLETED_INFRASTRUCTURE, then IN_PROGRESS, then COMMUNITY.
        Returns empty list if none found (template handles the default image).
        """
        images_extensions_query = Q()
        for ext in IMAGE_EXTENSIONS:
            images_extensions_query |= Q(url__icontains=ext)

        village_filter = (
            Q(adm__in=self._child_villages) |
            Q(task__activity__phase__village__in=self._child_villages)
        )

        completed = list(
            Attachment.objects.filter(
                village_filter,
                process_moment=Attachment.COMPLETED_INFRASTRUCTURE
            ).filter(images_extensions_query)[:3]
        )

        in_progress = []
        if not completed:
            in_progress = list(
                Attachment.objects.filter(
                    village_filter,
                    process_moment=Attachment.INFRASTRUCTURE_IN_PROGRESS
                ).filter(images_extensions_query)[:1]
            )

        slots_remaining = max_images - len(completed) - len(in_progress)
        community = list(
            Attachment.objects.filter(
                village_filter,
                process_moment=Attachment.COMMUNITY_PROCESS
            ).filter(images_extensions_query)[:slots_remaining]
        )

        return completed + in_progress + community

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _get_ethnic_groups_label(self) -> str:
        """
        Collects main_languages values from all child villages,
        splits by comma, deduplicates, and returns a sorted joined string.
        """
        raw_values = (
            self._child_villages
            .exclude(main_languages__isnull=True)
            .exclude(main_languages='')
            .values_list('main_languages', flat=True)
        )
        groups = set()
        for value in raw_values:
            for token in value.split(','):
                groups.add(token.strip())
        return ', '.join(sorted(groups))