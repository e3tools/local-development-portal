from django.urls import path
from django.conf.urls import include

from . import views, views_excel

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardTemplateView.as_view(), name='dashboard'),
    
    path('subprojects-sectors/', views.DashboardSubprojectsListView.as_view(), name='dashboard_subprojects_sectors'),
    path('subprojects-sectors-and-steps/', views.DashboardSubprojectsSectorsAndStepsListView.as_view(), name='dashboard_subprojects_sectors_and_steps'),
    path('subprojects-steps/', views.DashboardSubprojectsStepsListView.as_view(), name='dashboard_subprojects_steps'),

    path('download-excel-file/', views_excel.DownloadExcelFile.as_view(), name='dashboard_download_excel_file'),
]
