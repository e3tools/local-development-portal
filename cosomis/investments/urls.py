from django.urls import path, include

from .views import IndexListView, CartView
from .ajax_views import FillSelectFilters

app_name = 'investments'
urlpatterns = [
    path('', IndexListView.as_view(), name='home_investments'),
    path('cart', CartView.as_view(), name='cart'),
    path('ajax/', include([
        path('test', FillSelectFilters.as_view())
    ]))
]
