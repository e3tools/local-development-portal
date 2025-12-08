from django.urls import path
from . import views

app_name = 'export'

urlpatterns = [
    path('excel/', views.export_investments_to_excel, name='export_investments_excel'),
]