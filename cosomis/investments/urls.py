from django.urls import path

from .views import IndexListView, CartView

app_name = 'investments'
urlpatterns = [
    path('', IndexListView.as_view(), name='home_investments'),
    path('cart', CartView.as_view(), name='cart')
]
