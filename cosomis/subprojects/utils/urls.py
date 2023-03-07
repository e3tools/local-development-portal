from django.urls import path

from . import views

app_name = 'utils'
urlpatterns = [
    path('upload/image', views.UploadSuprojectImageView.as_view(), name='upload_image_to_aws3'), #The path to download Image file to aws3
    path('update/image', views.UpdateSuprojectImageView.as_view(), name='update_image'),
]
