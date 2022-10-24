from django.urls import path

from . import views

app_name = 'kobotoolbox'

urlpatterns = [
    path('kobo/', views.kobo, name='kobo')
]


