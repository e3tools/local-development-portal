from django.urls import path
from django.conf.urls import include

from administrativelevels import views

app_name = 'administrativelevels'

urlpatterns = [
    path('', views.AdministrativeLevelsListView.as_view(), name='list'), # Administrative levels list path
    path('search/', views.AdministrativeLevelSearchListView.as_view(), name='search'), # Administrative levels path to search
    path('create/', views.AdministrativeLevelCreateView.as_view(), name='create'), # Administrative level path to create
    path('detail/<int:pk>/', views.AdministrativeLevelDetailView.as_view(), name='detail'), #The path of the detail
    path('detail/<int:adm_id>/attachments/<path:url>/download/', views.attachment_download,
         name='attachment_download'),
    path('detail/<int:adm_id>/attachments/download-zip/', views.attachment_download_zip,
         name='attachment_download_zip'),

    path('village/<int:pk>/', views.VillageDetailView.as_view(), name='village_detail'),
    path('village/<int:adm_id>/attachments/', views.VillageAttachmentListView.as_view(), name='village_attachments'),

    path('commune/<int:pk>/', views.CommuneDetailView.as_view(), name='commune_detail'),
    path('commune/<int:adm_id>/attachments/', views.CommuneAttachmentListView.as_view(), name='commune_attachments'),

    path('canton/<int:pk>/', views.CantonDetailView.as_view(), name='canton_detail'),
    path('canton/<int:adm_id>/attachments/', views.CantonAttachmentListView.as_view(), name='canton_attachments'),

    path('region/<int:pk>/', views.RegionDetailView.as_view(), name='region_detail'),
    path('prefecture/<int:pk>/', views.PrefectureDetailView.as_view(), name='prefecture_detail'),
    # The path of the detail of village
    path('attachments/', views.AttachmentListView.as_view(), name='attachments'), # The path of the attachments list

    path('utils/', include('administrativelevels.utils.urls')),

]




