from django.urls import path
from django.conf.urls import include

from administrativelevels import views_components as views

app_name = 'components'

urlpatterns = [
    path('overview/<int:pk>/', views.AdministrativeLevelOverviewComponent.as_view(), name='overview'), 
    path('priorities/<int:pk>/', views.AdministrativeLevelPrioritiesComponent.as_view(), name='priorities'),
   
]


