from django.urls import path

from . import views

app_name = 'subprojects'
urlpatterns = [
    path('', views.SubprojectsListView.as_view(), name='list'),
    path('map', views.SubprojectsMapView.as_view(), name='map'),
    path('<int:pk>', views.SubprojectDetailView.as_view(), name='detail'),
    path('create', views.SubprojectCreateView.as_view(), name='create'),
    path('vulnerable-group/create', views.VulnerableGroupCreateView.as_view(), name='vulnerable_group_create'),
]
