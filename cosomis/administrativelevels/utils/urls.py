from django.urls import path

from . import views

app_name = 'utils'
urlpatterns = [
    # path('get-administrative-level-for-cvd-by-adl', views.GetAdministrativeLevelForCVDByADLView.as_view(),
    #      name='get_administrative_level_for_cvd_by_adl'),
    path('get-choices-for-next-administrative-level-no-condition', views.GetChoicesForNextAdministrativeLevelNoConditionView.as_view(),
         name='get_choices_for_next_administrative_level_no_condition'),
    path('get-choices-for-next-administrative-level', views.GetChoicesForNextAdministrativeLevelView.as_view(),
         name='get_choices_for_next_administrative_level'),
     # path('get-choices-for-next-administrative-level-by-geographical-unit',
     #      views.GetChoicesAdministrativeLevelByGeographicalUnitView.as_view(),
     #      name='get_choices_for_next_administrative_level_by_geographical_unit'),
    path('get-ancestor-administrative-levels', views.GetAncestorAdministrativeLevelsView.as_view(),
         name='get_ancestor_administrative_levels'),
    path('task-detail/<int:pk>', views.TaskDetailAjaxView.as_view(), name='task_detail'),
    path('attachments-filter', views.FillAttachmentSelectFilters.as_view(), name='attachment_filter'),
    path('sectors-codes', views.SectorCodesCSVView.as_view(), name='sectors_codes'),
    path('villages-codes', views.VillagesCodesCSVView.as_view(), name='villages_codes'),
    path('villages-coordinates', views.InitializeVillageCoordinatesView.as_view(), name='initialize_village_coordinates'),
]
