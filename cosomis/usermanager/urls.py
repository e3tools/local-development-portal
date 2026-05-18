from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from django.conf.urls import include
from .views import SignupView, EmailVerificationView

from usermanager.forms import EmailAuthenticationForm, PassCodeAuthenticationForm
from usermanager import views_change_password
from usermanager.tokens import jwt_views

app_name = 'usermanager'
urlpatterns = [
    path('', auth_views.LoginView.as_view(
        authentication_form=EmailAuthenticationForm,
        template_name='login.html',
        redirect_authenticated_user=True), name='login'),
    path('register/', SignupView.as_view(), name='signup'),
    path('pass-code-login/', auth_views.LoginView.as_view(
        authentication_form=PassCodeAuthenticationForm,
        template_name='login.html',
        redirect_authenticated_user=True), name='pass-code-login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('email-verification/<slug:confirm_email_token>', EmailVerificationView.as_view(), name='email-verification'),
    path('password-reset',
         auth_views.PasswordResetView.as_view(template_name='password_reset.html',
                                              email_template_name='email/password_reset.html',
                                              html_email_template_name='email/password_reset.html',
                                              success_url=reverse_lazy('usermanager:password_reset_done')),
         name='password_reset'),
    path('password-reset-done', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'),
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('usermanager:password_reset_complete')),
         name='password_reset_confirm'),
    path('password-reset-complete', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'),
         name='password_reset_complete'),

    
    path('user-manager-email-notification/', views_change_password.RestSendChangePasswordCode.as_view(), name='user_manager_email_notification'),
    path('change-password/', views_change_password.RestChangePassword.as_view(), name='change_password'),

    path('user/manager/token/', auth_views.TemplateView.as_view(template_name='token.html'), name='token'),
    path('user/manager/generate-token/', jwt_views.generate_token_view, name='generate_token'),
    
]
