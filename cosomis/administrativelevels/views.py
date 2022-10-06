from django.shortcuts import render
from django.views.generic import DetailView

from administrativelevels.models import Village


class VillageDetailView(DetailView):
    """Class to present the detail page of one village"""

    model = Village
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = 'Village'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    
    def get_context_data(self, **kwargs):
        context = super(VillageDetailView, self).get_context_data(**kwargs)
        return context