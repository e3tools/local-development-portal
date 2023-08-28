from django.urls import path

from . import views, views_steps

app_name = 'subprojects'

urlpatterns = [
    path('get-subprojects-by-user/', views.RestGetSubprojectsByUser.as_view(), name="get_subprojects_by_user"),
    path('get-subproject-by-user/<int:pk>/', views.RestGetSubprojectByUser.as_view(), name="get_subproject_by_user"),

    path('get-steps/', views_steps.RestGetSteps.as_view(), name="get_steps"),
    path('get-subproject-steps/<int:subproject_id>/', views_steps.RestGetSubprojectSteps.as_view(), name="get_subproject_steps"),
]


