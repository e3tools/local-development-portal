from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import generic
from django.conf import settings
from cosomis.mixins import AJAXRequestMixin, PageMixin
from .forms import SubprojectForm
from subprojects.models import Subproject
from django.utils.translation import gettext_lazy
from django import forms

# Create your views here.

class SubprojectsListView(PageMixin, LoginRequiredMixin, generic.ListView):
    model = Subproject
    queryset = Subproject.objects.all()
    template_name = 'subprojects_list.html'
    context_object_name = 'subprojects'
    title = 'Subprojects'
    active_level1 = 'subprojects'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_queryset(self):
        return super().get_queryset()

class SubprojectsMapView(LoginRequiredMixin, generic.ListView):

    model = Subproject
    queryset = Subproject.objects.all()
    template_name = 'subprojects_map.html'
    context_object_name = 'subprojects'
    title = 'Subprojects'
    active_level1 = 'subprojects'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['access_token'] = settings.MAPBOX_ACCESS_TOKEN
        context['lat'] = settings.DIAGNOSTIC_MAP_LATITUDE
        context['lng'] = settings.DIAGNOSTIC_MAP_LONGITUDE
        context['zoom'] = settings.DIAGNOSTIC_MAP_ZOOM
        context['ws_bound'] = settings.DIAGNOSTIC_MAP_WS_BOUND
        context['en_bound'] = settings.DIAGNOSTIC_MAP_EN_BOUND
        context['country_iso_code'] = settings.DIAGNOSTIC_MAP_ISO_CODE
        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Return a response, using the `response_class` for this view, with a
        template rendered with the given context.
        Pass response_kwargs to the constructor of the response class.
        """
        response_kwargs.setdefault('content_type', self.content_type)
        return self.response_class(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            using=self.template_engine,
            **response_kwargs
        )


class SubprojectDetailView(LoginRequiredMixin, generic.DetailView):
    model = Subproject
    template_name = 'subproject.html'
    context_object_name = 'subproject'
    title = 'Subproject'
    active_level1 = 'subprojects'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]


class SubprojectCreateView(PageMixin, LoginRequiredMixin, generic.CreateView):
    model = Subproject
    template_name = 'subproject_create.html'
    context_object_name = 'subproject'
    title = 'Create Subproject'
    active_level1 = 'subprojects'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
 
    form_class = SubprojectForm # specify the class form to be displayed

    def post(self, request, *args, **kwargs):
        form = SubprojectForm(request.POST)
        if form.is_valid():
            subproject = form.save()
            subproject.save()
            return redirect('subprojects:list')
        return super(SubprojectCreateView, self).get(request, *args, **kwargs)
        
