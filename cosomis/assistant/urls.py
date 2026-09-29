from django.urls import path

from assistant import views

app_name = "assistant"
urlpatterns = [
    path("", views.ChatView.as_view(), name="chat"),
    path("panel/", views.PanelView.as_view(), name="panel"),
    path("send/", views.SendView.as_view(), name="send"),
    path("new/", views.NewConversationView.as_view(), name="new"),
    path("reports/<uuid:token>/<str:fmt>/", views.ReportDownloadView.as_view(), name="report"),
    path("messages/<int:pk>/export/<str:fmt>/", views.MessageExportView.as_view(), name="export"),
]
