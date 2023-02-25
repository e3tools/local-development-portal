from django.urls import path

from . import views

app_name = 'utils'
urlpatterns = [
    path('get-choices-for-next-administrative-level', views.GetChoicesForNextAdministrativeLevelView.as_view(),
         name='get_choices_for_next_administrative_level'),
     path('get-choices-for-next-administrative-level-by-geographical-unit', 
          views.GetChoicesAdministrativeLevelByGeographicalUnitView.as_view(),
          name='get_choices_for_next_administrative_level_by_geographical_unit'),
    path('get-ancestor-administrative-levels', views.GetAncestorAdministrativeLevelsView.as_view(),
         name='get_ancestor_administrative_levels'),
]
