from django.urls import path
from django.conf.urls import include

from subprojects import views_components as views

app_name = 'components'

urlpatterns = [
    path('common/<int:pk>/<int:canton_id>/', views.SubprojectCommonComponent.as_view(), name='common'), 
    path('by-sector-and-administrative-level/<int:pk>/', views.SubprojectsBySectorANdAdministrativeLevelComponent.as_view(), name='by_sector_and_administrative_level'), 
    path('by-administrative-level/<int:pk>/', views.SummarySubprojectsByAdministrativeLevelComponent.as_view(), name='by_administrative_level'), 
   
]

