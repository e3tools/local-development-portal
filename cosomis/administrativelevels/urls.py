from django.urls import path

from administrativelevels import views

app_name = 'administrativelevels'

urlpatterns = [
    path('', views.AdministrativeLevelsListView.as_view(), name='list'), # Administrative levels list path
    path('village-detail/<int:pk>/', views.VillageDetailView.as_view(), name='village_detail'), #The path of the detail of village
    path('upload/', views.UploadCSVView.as_view(), name='upload'), #The path to download CSV/Excel file from db
    path('download/', views.DownloadCSVView.as_view(), name='download'), #The path to upload CSV file and save in db
    path('village/<int:administrative_level_id>/obstacles', views.ObstaclesListView.as_view(), name='priorities_obstacles'),
    path('village/obstacles/<int:obstacle_id>/delete', views.obstacle_delete, name='obstacle_delete'), #The path to delete obstacle
    path('village/<int:administrative_level_id>/goals', views.GoalsListView.as_view(), name='priorities_goals'),
    path('village/goals/<int:goal_id>/delete', views.goal_delete, name='goal_delete'), #The path to delete goal
    path('village/<int:administrative_level_id>/priorities', views.PrioritiesListView.as_view(), name='priorities_priorities'),
    path('village/priorities/<int:priority_id>/delete', views.priority_delete, name='priority_delete'), #The path to delete priority
]


