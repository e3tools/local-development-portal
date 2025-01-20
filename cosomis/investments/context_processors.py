from django.conf import settings
from datetime import datetime, timedelta
from investments.models import Package
from usermanager.models import User
from django.db.models import Count


def notifications(request):
    resp = {
            'pending_approvals': 0,
            'has_urgent_approvals': False
        }
    try:
        if request.user.is_moderator:
            max_response_day = settings.MAX_RESPONSE_DAYS if hasattr(settings, 'MAX_RESPONSE_DAYS') else 3
            urgent_day = datetime.now() - timedelta(days=max_response_day)

            packages_qs = Package.objects.annotate(
                investments_count=Count('funded_investments')
            ).filter(status=Package.PENDING_APPROVAL).exclude(investments_count=0)
            users_qs = User.objects.filter(is_approved=None, is_moderator=False)

            has_urgent_packages = packages_qs.filter(updated_date__lte=urgent_day).exists()
            has_urgent_users = users_qs.filter(date_joined__lte=urgent_day).exists()

            resp = {
                'pending_approvals': packages_qs.count() + users_qs.count(),
                'has_urgent_approvals': has_urgent_packages or has_urgent_users
            }
        else:
            max_response_day = settings.MAX_RESPONSE_DAYS if hasattr(settings, 'MAX_RESPONSE_DAYS') else 3
            urgent_day = datetime.now() - timedelta(days=max_response_day)
            last_login_date = request.user.last_login - timedelta(days=max_response_day*10)

            packages_qs = Package.objects.filter(status__in=[Package.APPROVED, Package.REJECTED],
                                                 acknowledge_by_investor=False,
                                                 user_id=request.user.id,
                                                 updated_date__gte=last_login_date)

            has_urgent_packages = packages_qs.filter(updated_date__lte=urgent_day).exists()

            resp = {
                'pending_approvals': packages_qs.count(),
                'has_urgent_approvals': has_urgent_packages
            }
        return resp
    except (TypeError, AttributeError):
        return resp


def cart_items(request):
    try:
        package = Package.objects.get_active_cart(
            user=request.user
        )
        return {
            'cart_items': package.funded_investments.all().count()
        }
    except TypeError:
        return {
            'cart_items': 0
        }
