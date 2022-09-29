from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import generic
from cosomis.mixins import AJAXRequestMixin, PageMixin
from subprojects.models import Subproject
from django.utils.translation import gettext_lazy

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

