from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce
from cosomis.constants import IMAGE_EXTENSIONS
from administrativelevels.models import AdministrativeLevel
from investments.models import Attachment, Investment

# The canton development plan is the file uploaded under this label on the
# cantonal arbitration task, which each project words differently. Every
# headquarters village's cycle carries a copy of that task.
CANTON_PLAN_TASK_NAMES = (
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage, la sélection des sous - projets "
    "à financer et l'affection des ressources par sous - projet",  # COSO
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage, la sélection des sous - projets "
    "à financer et l'affectation des ressources par sous - projet",  # FA-COSO
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage des priorités pour la rédaction du PDC.",  # PURS
)
CANTON_PLAN_ATTACHMENT_NAME = "Télecharger le document du plan d'actions cantonales finalisé"


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

            priority_count_not_funded=Count(
                'id',
                filter=Q(project_status=Investment.NOT_FUNDED)
            ),
            priority_count_funded=Count(
                'id',
                filter=~Q(project_status=Investment.NOT_FUNDED)
            ),
            total_estimated_cost_not_funded=Coalesce(
                Sum(
                    'estimated_cost',
                    filter=Q(project_status=Investment.NOT_FUNDED)
                ),
                0
            ),
            total_estimated_cost_funded=Coalesce(
                Sum(
                    'estimated_cost',
                    filter=~Q(project_status=Investment.NOT_FUNDED)
                ),
                0
            ),
        )

        # CVD count: geographical units linked to child villages
        cvd_count = (
            self._child_villages
            .filter(is_headquarters=True)
            .values('id')
            .distinct()
            .count()
        )

        return {
            'village_count': self._child_villages.count(),
            'cvd_count': cvd_count,
            **investment_agg,
            # 'priority_count': investment_agg['priority_count'],
            # 'total_estimated_cost': investment_agg['total_estimated_cost'],
        }

    def get_development_plans(self) -> list:
        """
        Returns the canton development plan of each project as
        (project name, Attachment) pairs ordered by project name: the most
        recently validated copy among the child villages' tasks.
        """
        plans = (
            Attachment.objects.filter(
                name=CANTON_PLAN_ATTACHMENT_NAME,
                task__name__in=CANTON_PLAN_TASK_NAMES,
                task__validated=True,
                task__activity__phase__village__in=self._child_villages,
            )
            .exclude(url__startswith='file:')  # still on the tablet, never uploaded
            .annotate(project_name=F('task__activity__phase__project__name'))
            .order_by(F('task__date_validated').desc(nulls_last=True), '-id')
            .only('id', 'url')
        )
        latest = {}
        for plan in plans:
            latest.setdefault(plan.project_name, plan)
        return sorted(latest.items(), key=lambda item: item[0] or '')

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