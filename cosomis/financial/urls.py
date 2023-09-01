from django.urls import path
from django.conf.urls import include

from financial import views 

app_name = 'financial'



urlpatterns = [
    path('allocations', views.AdministrativeLevelAllocationsListView.as_view(), name='allocations_list'), # allocations list path
    path('allocation/create/', views.AdministrativeLevelAllocationCreateView.as_view(), name='allocation_create'), # allocation path to create
    path('allocation/update/<int:pk>/', views.AdministrativeLevelAllocationUpdateView.as_view(), name='allocation_update'), # allocation path to update
    path('allocation/detail/<int:pk>/', views.AdministrativeLevelAllocationDetailView.as_view(), name='allocation_detail'), #The path of the detail of allocation
]