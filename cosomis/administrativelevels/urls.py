from django.urls import path

from administrativelevels.views import VillageDetailView
from administrativelevels.views import UploadCSVView

app_name = 'administrativelevels'

urlpatterns = [
    path('village-detail/<int:pk>/', VillageDetailView.as_view(), name='village_detail'), #The path of the detail of village
    path('upload/', UploadCSVView.as_view(), name='upload'), #The path to upload CSV file and save in db
]


