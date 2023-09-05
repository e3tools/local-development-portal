from django.urls import path
from django.conf.urls import include

from financial import (
    views, views_bank_transfer, views_disbursement_request,
    views_disbursement
)

app_name = 'financial'



urlpatterns = [
    path('', views.FinancialTemplateView.as_view(), name='financials'), # financial path
    path('allocations', views.AdministrativeLevelAllocationsListView.as_view(), name='allocations_list'), # allocations list path
    path('allocation/create/', views.AdministrativeLevelAllocationCreateView.as_view(), name='allocation_create'), # allocation path to create
    path('allocation/update/<int:pk>/', views.AdministrativeLevelAllocationUpdateView.as_view(), name='allocation_update'), # allocation path to update
    path('allocation/detail/<int:pk>/', views.AdministrativeLevelAllocationDetailView.as_view(), name='allocation_detail'), #The path of the detail of allocation

    path('bank-transfers', views_bank_transfer.BankTransfersListView.as_view(), name='bank_transfers_list'), # bank transfers list path
    path('bank-transfer/create/', views_bank_transfer.BankTransferCreateView.as_view(), name='bank_transfer_create'), # bank transfer path to create
    path('bank-transfer/update/<int:pk>/', views_bank_transfer.BankTransferUpdateView.as_view(), name='bank_transfer_update'), # bank transfer path to update
    path('bank-transfer/detail/<int:pk>/', views_bank_transfer.BankTransferDetailView.as_view(), name='bank_transfer_detail'), #The path of the detail of bank transfer
    
    path('disbursement-requests', views_disbursement_request.DisbursementRequestsListView.as_view(), name='disbursement_requests_list'),
    path('disbursement-request/create/', views_disbursement_request.DisbursementRequestCreateView.as_view(), name='disbursement_request_create'), 
    path('disbursement-request/update/<int:pk>/', views_disbursement_request.DisbursementRequestUpdateView.as_view(), name='disbursement_request_update'), 
    path('disbursement-request/detail/<int:pk>/', views_disbursement_request.DisbursementRequestDetailView.as_view(), name='disbursement_request_detail'), 

    path('disbursements', views_disbursement.DisbursementsListView.as_view(), name='disbursements_list'),
    path('disbursement/create/', views_disbursement.DisbursementCreateView.as_view(), name='disbursement_create'), 
    path('disbursement/update/<int:pk>/', views_disbursement.DisbursementUpdateView.as_view(), name='disbursement_update'), 
    path('disbursement/detail/<int:pk>/', views_disbursement.DisbursementDetailView.as_view(), name='disbursement_detail'), 
]