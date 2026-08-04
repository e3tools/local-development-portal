from django.db.models import Count, Q

from usermanager.models import User
from .models import Investment


def get_organization_account_stats():
    """Comptes créés/approuvés et investissements par organisation.

    Partagé entre la page de notifications modérateur et le tableau de bord.
    """
    queryset = (
        User._default_manager.filter(is_moderator=False)
        .values("organization_id", "organization__name")
        .annotate(
            total_accounts=Count("id"),
            approved_accounts=Count("id", filter=Q(is_approved=True)),
        )
        .order_by("organization__name")
    )

    # Calculé séparément (plutôt qu'en annotation combinée sur le même
    # queryset) pour éviter le gonflement classique des Count() de Django
    # quand deux relations one-to-many différentes sont agrégées ensemble.
    investments_by_organization = dict(
        Investment.objects.filter(funded_by__organization_id__isnull=False)
        .values("funded_by__organization_id")
        .annotate(total=Count("id"))
        .values_list("funded_by__organization_id", "total")
    )

    stats = list(queryset)
    for stat in stats:
        stat["total_investments"] = investments_by_organization.get(
            stat["organization_id"], 0
        )
    return stats
