from django.contrib.auth.mixins import AccessMixin
from django.http import Http404, JsonResponse

from utils.mixpanel.utils import track_user_activity


class PageMixin(object):
    title = None
    active_level1 = None
    active_level2 = None
    breadcrumb = None
    form_mixin = None

    def get_context_data(self, **kwargs):
        ctx = super(PageMixin, self).get_context_data(**kwargs)
        ctx.setdefault('title', self.title)
        ctx.setdefault('active_level1', self.active_level1)
        ctx.setdefault('active_level2', self.active_level2)
        ctx.setdefault('breadcrumb', self.breadcrumb)
        ctx.setdefault('form_mixin', self.form_mixin)
        return ctx

    
    def dispatch(self, request, *args, **kwargs):
        
        track_user_activity(request, self.__class__.__name__)
        
        return super().dispatch(request, *args, **kwargs)
    


class ModalFormMixin(object):
    template_name = 'common/modal_form.html'
    id_form = 'form'
    title = None
    subtitle = None
    picture = None
    picture_class = None
    submit_button = None
    form_class_color = 'primary'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.setdefault('id_form', self.id_form)
        ctx.setdefault('title', self.title)
        ctx.setdefault('subtitle', self.subtitle)
        ctx.setdefault('picture', self.picture)
        ctx.setdefault('picture_class', self.picture_class)
        ctx.setdefault('submit_button', self.submit_button)
        ctx.setdefault('form_class_color', self.form_class_color)
        return ctx


class AJAXRequestMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            raise Http404
        return super().dispatch(request, *args, **kwargs)


class JSONResponseMixin:
    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        return context


class LoginRequiredApproveRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_approved:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
