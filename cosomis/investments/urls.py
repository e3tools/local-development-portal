from django.urls import path, include

from .views import IndexListView, CartView, ProfileTemplateView
from .ajax_views import FillAdmLevelsSelectFilters, FillSectorsSelectFilters

app_name = 'investments'
urlpatterns = [
    path('', IndexListView.as_view(), name='home_investments'),
    path('cart', CartView.as_view(), name='cart'),
    path('profile', ProfileTemplateView.as_view(), name='profile'),
    path('ajax/', include([
        path('adm-levels', FillAdmLevelsSelectFilters.as_view()),
        path('sectors', FillSectorsSelectFilters.as_view()),
    ]))
]
