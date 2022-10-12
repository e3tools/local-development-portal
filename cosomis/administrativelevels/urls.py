from django.urls import path

from administrativelevels.views import VillageDetailView
from administrativelevels.views import AdministrativeLevelsListView
from administrativelevels.views import UploadCSVView

app_name = 'administrativelevels'

urlpatterns = [
    path('', AdministrativeLevelsListView.as_view(), name='list'), # Administrative levels list path
    path('village-detail/<int:pk>/', VillageDetailView.as_view(), name='village_detail'), #The path of the detail of village
    path('upload/', UploadCSVView.as_view(), name='upload'), #The path to upload CSV file and save in db
]


