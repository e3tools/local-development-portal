from django.urls import path

from cdd_funnel.views import CddFunnelView, StageDrilldownView

app_name = 'cdd_funnel'
urlpatterns = [
    path('', CddFunnelView.as_view(), name='main_funnel'),
    path(
        'stage/<str:stage_key>/',
        StageDrilldownView.as_view(),
        name='stage_drilldown',
    ),
]
