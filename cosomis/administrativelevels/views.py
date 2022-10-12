from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import DetailView, TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from cosomis.mixins import PageMixin
from django.http import Http404
import pandas as pd

from administrativelevels.models import AdministrativeLevel
from administrativelevels.libraries import convert_file_to_dict
from administrativelevels import functions as administrativelevels_functions


class VillageDetailView(PageMixin, LoginRequiredMixin, DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
    template_name = 'village_detail.html'
    context_object_name = 'village'
    title = 'Village'
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    
    def get_context_data(self, **kwargs):
        context = super(VillageDetailView, self).get_context_data(**kwargs)

        if context.get("object") and context.get("object").type == "Village" : # Verify if the administrativeLevel type is Village
            return context
        raise Http404
        


class UploadCSVView(PageMixin, LoginRequiredMixin, TemplateView):
    """Class to upload and save the administrativelevels"""

    template_name = 'upload.html'
    context_object_name = 'Upload'
    title = "Upload"
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def post(self, request, *args, **kwargs):
        datas = {}
        try:
            datas = convert_file_to_dict.conversion_file_csv_to_dict(request.FILES.get('file'))
        except pd.errors.ParserError as exc:
            datas = convert_file_to_dict.conversion_file_xlsx_to_dict(request.FILES.get('file'))
        except Exception as exc:
            messages.info(request, "An error has occurrd...")
        
        message = administrativelevels_functions.save_csv_file_datas_in_db(datas) # call function to save CSV datas in database
        if message:
            messages.info(request, message)

        return redirect('administrativelevels:upload')
    
    def get(self, request, *args, **kwargs):
        context = super(UploadCSVView, self).get(request, *args, **kwargs)
        return context


class AdministrativeLevelsListView(PageMixin, LoginRequiredMixin, ListView):
    """Display administrative level list"""

    model = AdministrativeLevel
    queryset = AdministrativeLevel.objects.filter(type="Village")
    template_name = 'administrativelevels_list.html'
    context_object_name = 'administrativelevels'
    title = 'Administrative levels'
    active_level1 = 'administrative_levels'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_queryset(self):
        return super().get_queryset()
