from django.views import generic
from django.shortcuts import resolve_url
from django.conf import settings
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.views import RedirectURLMixin
from django.http import HttpResponseRedirect
from .forms import UserCreationForm


User = get_user_model()


class SignupView(RedirectURLMixin, generic.CreateView):
    form_class = UserCreationForm
    queryset = User.objects.all()
    template_name = 'register.html'

    def form_valid(self, form):
        self.object = form.save()
        auth_login(self.request, self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_default_redirect_url(self):
        """Return the default redirect URL."""
        if self.next_page:
            return resolve_url(self.next_page)
        else:
            return resolve_url(settings.LOGIN_REDIRECT_URL)


class EmailVerificationView(generic.TemplateView):
    template_name = 'email_confirmed_successfully.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = User.objects.get(confirm_email_token=self.kwargs['confirm_email_token'])
        user.email_was_confirm = True
        user.confirm_email_token = None
        user.save()
        return context
