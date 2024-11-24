from django.urls import path
from rest_framework import routers

from cdd_funnel.views import CddFunnelView

router = routers.DefaultRouter()

app_name = 'cdd_funnel'
urlpatterns = [
    path('', CddFunnelView.as_view(), name='main_funnel'),
]
