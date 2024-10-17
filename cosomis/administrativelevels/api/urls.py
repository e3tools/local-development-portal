from django.urls import path

from . import views

app_name = 'administrativelevels'

urlpatterns = [
    path('get-administrative-levels-by-user/<str:type_adl>/<str:project_id>/', views.RestGetAdministrativeLevelByUser.as_view(), name="get_administrative_levels_by_user"),
    path('get-cvds-by-user/<str:project_id>/', views.RestGetACVDByUser.as_view(), name="get_cvds_by_user"),
]


