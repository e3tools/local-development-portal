from django.urls import path

from .views import IndexListView

app_name = 'investments'
urlpatterns = [
    path('', IndexListView.as_view(), name='home_investments')
]
