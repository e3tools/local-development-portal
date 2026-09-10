from django.urls import path

from assistant import views

app_name = "assistant"
urlpatterns = [
    path("", views.ChatView.as_view(), name="chat"),
    path("send/", views.SendView.as_view(), name="send"),
    path("new/", views.NewConversationView.as_view(), name="new"),
]
