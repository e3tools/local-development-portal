from django.urls import path
from django.conf.urls import include

from . import views

app_name = 'subprojects'
urlpatterns = [
    path('', views.SubprojectsListView.as_view(), name='list'),
    path('map', views.SubprojectsMapView.as_view(), name='map'),
    path('<int:pk>', views.SubprojectDetailView.as_view(), name='detail'),
    path('create', views.SubprojectCreateView.as_view(), name='create'),
    path('update/<int:pk>/', views.SubprojectUpdateView.as_view(), name='update'),
    path('vulnerable-group/create', views.VulnerableGroupCreateView.as_view(), name='vulnerable_group_create'),
    path('image/<int:image_id>/delete', views.subprojectimage_delete, name='subproject_image_delete'),

    path('download/', views.DownloadCSVView.as_view(), name='download'), #The path to upload CSV file and save in db

    path('utils/', include('subprojects.utils.urls')),
]
