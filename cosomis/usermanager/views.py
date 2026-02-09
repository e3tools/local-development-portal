from django.views import generic
from django.shortcuts import resolve_url
from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.views import RedirectURLMixin
from django.http import HttpResponseRedirect
from django.views.generic import TemplateView
from .forms import UserCreationForm
from django.shortcuts import redirect
from django.contrib import messages

from utils.mixpanel.utils import track_user_activity

User = get_user_model()


class SignupView(RedirectURLMixin, generic.CreateView):
    form_class = UserCreationForm
    queryset = User.objects.all()
    template_name = 'register.html'

    def form_valid(self, form):
        self.object = form.save()
        auth_login(self.request, self.object)
        track_user_activity(self.request, "UserLoggedOut")
        return HttpResponseRedirect(self.get_success_url())

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url(settings.LOGIN_REDIRECT_URL)


# class EmailVerificationView(generic.TemplateView):
#     template_name = 'email_confirmed_successfully.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = User.objects.get(confirm_email_token=self.kwargs['confirm_email_token'])
#         user.email_was_confirm = True
#         user.confirm_email_token = None
#         user.save()
#         return context
class EmailVerificationView(TemplateView):
    template_name = 'email_confirmed_successfully.html'

    def dispatch(self, request, *args, **kwargs):
        token = self.kwargs.get('confirm_email_token')

        try:
            user = User.objects.get(confirm_email_token=token, email_was_confirm=False)
            user.email_was_confirm = True
            user.confirm_email_token = None
            user.save()

            messages.success(request, "Votre adresse e-mail a été confirmée avec succès.")

            track_user_activity(self.request, "UserConfirmedEmail")

        except User.DoesNotExist:
            messages.error(request, "Le lien de vérification est invalide ou a expiré.")
            return redirect(settings.LOGIN_REDIRECT_URL)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['email_confirmed'] = True
        return context
