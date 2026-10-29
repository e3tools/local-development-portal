"""
Category review: staff browse investments by category/sector, correct the
misclassified ones and mark the rest as verified.

Kept out of the views so the rules (cost follows the sector, every change is
logged, an undo restores the exact previous state) live in one place.
"""

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone

from administrativelevels.models import Sector
from .constants import DEFAULT_ESTIMATED_COST, SECTOR_ESTIMATED_COSTS
from .models import Investment, InvestmentSectorChange

# Values of the "verified" filter
VERIFIED_TODO = "todo"
VERIFIED_DONE = "done"
VERIFIED_ALL = "all"
VERIFIED_CHOICES = (VERIFIED_TODO, VERIFIED_DONE, VERIFIED_ALL)


class StaleChangeError(Exception):
    """The investment's sector moved on since the change being undone."""


def estimated_cost_for(sector):
    """Same rule as update_investment_estimated_costs_by_sector_bj."""
    return SECTOR_ESTIMATED_COSTS.get(sector.name, DEFAULT_ESTIMATED_COST)


def grouped_sectors():
    """[(category, [sectors...]), ...] sorted by name, for grouped <select>s."""
    sectors = Sector.objects.select_related("category").order_by("category__name", "name")
    groups = {}
    for sector in sectors:
        groups.setdefault(sector.category, []).append(sector)
    return list(groups.items())


class ReviewFilters:
    """The listing filters, parsed from a GET QueryDict."""

    def __init__(self, params):
        self.category_ids = [v for v in params.getlist("category-filter") if v.isdigit()]
        self.sector_ids = [v for v in params.getlist("sector-filter") if v.isdigit()]
        self.query = params.get("q", "").strip()
        # The switch is on by default: an unchecked checkbox sends nothing, so
        # "submitted" tells a first visit apart from a deliberate "off".
        if params.get("submitted"):
            self.exclude_funded = bool(params.get("exclude-funded"))
        else:
            self.exclude_funded = True
        verified = params.get("verified", VERIFIED_TODO)
        self.verified = verified if verified in VERIFIED_CHOICES else VERIFIED_TODO

    def base_queryset(self):
        """Every filter except "verified" (the progress counter ignores it)."""
        qs = Investment.objects.filter(
            investment_status__in=[Investment.PRIORITY, Investment.SUBPROJECT]
        )
        if self.category_ids:
            qs = qs.filter(sector__category__id__in=self.category_ids)
        if self.sector_ids:
            qs = qs.filter(sector__id__in=self.sector_ids)
        if self.query:
            qs = qs.filter(title__icontains=self.query)
        if self.exclude_funded:
            qs = qs.filter(project_status=Investment.NOT_FUNDED)
        return qs

    def queryset(self):
        qs = self.base_queryset()
        if self.verified == VERIFIED_TODO:
            qs = qs.filter(category_verified_at__isnull=True)
        elif self.verified == VERIFIED_DONE:
            qs = qs.filter(category_verified_at__isnull=False)
        return with_card_data(qs).order_by("title", "id")

    def progress(self):
        return self.base_queryset().aggregate(
            total=Count("id"),
            verified=Count("id", filter=Q(category_verified_at__isnull=False)),
        )


def with_card_data(qs):
    """What a review card renders, in one query (no per-card lookups)."""
    return qs.select_related(
        "sector__category",
        "administrative_level__parent__parent",
    ).only(
        "id", "title", "description", "estimated_cost", "project_status",
        "category_verified_at",
        "sector__id", "sector__name", "sector__category__id", "sector__category__name",
        "administrative_level__id", "administrative_level__name",
        "administrative_level__parent__id",
        "administrative_level__parent__parent__id",
        "administrative_level__parent__parent__name",
    ).annotate(
        has_sector_changes=Exists(
            InvestmentSectorChange.objects.filter(investment=OuterRef("pk"))
        )
    )


def _mark_verified_fields(investment, user):
    investment.category_verified_at = timezone.now()
    investment.category_verified_by = user


@transaction.atomic
def change_sector(investment, new_sector, user):
    """Move an investment to another sector; its cost follows the sector.

    Returns the logged InvestmentSectorChange, or None when the sector is
    unchanged (the investment is then just confirmed as verified).
    """
    investment = Investment.objects.select_for_update().get(pk=investment.pk)
    if investment.sector_id == new_sector.id:
        _mark_verified_fields(investment, user)
        investment.save(update_fields=["category_verified_at", "category_verified_by"])
        return None

    change = InvestmentSectorChange.objects.create(
        investment=investment,
        old_sector_id=investment.sector_id,
        new_sector=new_sector,
        old_estimated_cost=investment.estimated_cost,
        new_estimated_cost=estimated_cost_for(new_sector),
        changed_by=user,
    )
    investment.sector = new_sector
    investment.estimated_cost = change.new_estimated_cost
    _mark_verified_fields(investment, user)
    investment.save(update_fields=[
        "sector", "estimated_cost", "category_verified_at", "category_verified_by",
        "updated_date",
    ])
    return change


@transaction.atomic
def undo_change(change, user):
    """Restore the exact sector and cost from before `change`, and log it."""
    investment = Investment.objects.select_for_update().get(pk=change.investment_id)
    if (
        change.undoes_id is not None
        or change.undone_by.exists()
        or investment.sector_id != change.new_sector_id
        or change.old_sector_id is None
    ):
        raise StaleChangeError()

    undo = InvestmentSectorChange.objects.create(
        investment=investment,
        old_sector_id=investment.sector_id,
        new_sector_id=change.old_sector_id,
        old_estimated_cost=investment.estimated_cost,
        new_estimated_cost=change.old_estimated_cost,
        changed_by=user,
        undoes=change,
    )
    investment.sector_id = change.old_sector_id
    investment.estimated_cost = change.old_estimated_cost
    # Undoing means "the original sector was right": still a verified answer.
    _mark_verified_fields(investment, user)
    investment.save(update_fields=[
        "sector", "estimated_cost", "category_verified_at", "category_verified_by",
        "updated_date",
    ])
    return undo


def mark_verified(investment_ids, user):
    """Confirm the sector of several investments; returns how many changed."""
    return Investment.objects.filter(
        id__in=investment_ids, category_verified_at__isnull=True
    ).update(category_verified_at=timezone.now(), category_verified_by=user)


def history(investment):
    return investment.sector_changes.select_related(
        "old_sector__category", "new_sector__category", "changed_by", "undoes"
    )
