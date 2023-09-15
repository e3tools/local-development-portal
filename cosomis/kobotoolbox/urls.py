from django.urls import path

from . import views

app_name = 'kobotoolbox'

urlpatterns = [
    path('kobo/', views.kobo, name='kobo'),
    path('gms/', views.get_gms_form_reponse, name='kobo_gms'),
    path('gms-save-images/', views.get_gms_form_reponse_save_images, name='kobo_gms_save_mages')
]


