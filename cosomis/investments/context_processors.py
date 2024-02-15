from investments.models import Package


def notifications(request):  # If moderator
    packages_count = Package.objects.filter(status=Package.PENDING_APPROVAL).count()
    return {
        'pending_packages': packages_count
    }


def cart_items(request):
    package = Package.objects.get_active_cart(
        user=request.user
    )
    return {
        'cart_items': package.funded_investments.all().count()
    }
