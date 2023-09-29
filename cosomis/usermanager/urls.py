from django.contrib.auth import views as auth_views
from django.urls import path

from usermanager.forms import EmailAuthenticationForm
from usermanager.forms import PassCodeAuthenticationForm

app_name = 'usermanager'
urlpatterns = [
    path('', auth_views.LoginView.as_view(
        authentication_form=EmailAuthenticationForm,
        template_name='login.html',
        redirect_authenticated_user=True), name='login'),
     path('pass-code-login/', auth_views.LoginView.as_view(
        authentication_form=PassCodeAuthenticationForm,
        template_name='login.html',
        redirect_authenticated_user=True), name='pass-code-login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout')
]
