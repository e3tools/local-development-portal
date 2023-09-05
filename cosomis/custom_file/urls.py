from django.urls import path
from django.conf.urls import include

from custom_file import views

app_name = 'custom_file'



urlpatterns = [
    path('upload-file', views.UploadFileFormView.as_view(), name='upload_file')
]