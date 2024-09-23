from django.urls import path, include
from rest_framework import routers

from .views import (
    IndexListView, CartView,
    ProfileTemplateView, ModeratorApprovalsListView,
    ModeratorPackageReviewView, PackageDetailView
)
from .ajax_views import FillAdmLevelsSelectFilters, FillSectorsSelectFilters, InvestmentModelViewSet

router = routers.DefaultRouter()
router.register(r'datatable', InvestmentModelViewSet)

app_name = 'investments'
urlpatterns = [
    path('', IndexListView.as_view(), name='home_investments'),
    path('cart', CartView.as_view(), name='cart'),
    path('profile', ProfileTemplateView.as_view(), name='profile'),
    path('package/<int:pk>', PackageDetailView.as_view(), name='package_detail'),
    path('moderator/', include([
        path('notifications', ModeratorApprovalsListView.as_view(), name='notifications'),
        path('review/<int:package>', ModeratorPackageReviewView.as_view(), name='package_review'),
    ])),
    path('ajax/', include([
        path('adm-levels', FillAdmLevelsSelectFilters.as_view()),
        path('sectors', FillSectorsSelectFilters.as_view()),
    ] + router.urls))
]
