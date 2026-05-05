from django.urls import path
from .register_user import RegisterUsersByUploadingExcelAPIView



urlpatterns = [
    path('register-users-by-excel/', RegisterUsersByUploadingExcelAPIView.as_view()),
]