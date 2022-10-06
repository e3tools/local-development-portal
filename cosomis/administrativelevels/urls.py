from django.urls import path

from administrativelevels.views import VillageDetailView

app_name = 'administrativelevels'

urlpatterns = [
    path('village-detail/<int:pk>/', VillageDetailView.as_view(), name='village_detail'), #The path of the detail of village
]