from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import DetailView, TemplateView
import pandas as pd

from administrativelevels.models import AdministrativeLevel
from administrativelevels.libraries import convert_file_to_dict
from administrativelevels import functions as administrativelevels_functions


class VillageDetailView(DetailView):
    """Class to present the detail page of one village"""

    model = AdministrativeLevel
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



class UploadCSVView(TemplateView):
    """Class to upload and save the administrativelevels"""

    template_name = 'upload.html'
    context_object_name = 'Upload'
    title = "Upload"
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
    
