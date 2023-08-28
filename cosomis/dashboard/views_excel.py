from django.views.generic import View
from cosomis.mixins import AJAXRequestMixin, JSONResponseMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.http import Http404
import json
import os
from datetime import datetime
import pandas as pd
from sys import platform

from administrativelevels.libraries import download_file




class DownloadExcelFile(AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, View):
    template_name = 'statistics/subprojects_tracking.html'
    context_object_name = 'Download'
    title = gettext_lazy("Download")

    def post(self, request, *args, **kwargs):
        input_json = json.loads(request.body)
        datas = input_json.get('datas')
        type_datas = input_json.get('type_datas')

        try:
            if not os.path.exists("static/excel/subprojects"):
                os.makedirs("static/excel/subprojects")

            file_name = type_datas if type_datas else "summary_subprojects_excel"

            
            file_path = "excel/subprojects/" + file_name + str(datetime.today().replace(microsecond=0)).replace("-", "").replace(":", "").replace(" ", "_") +".xlsx"
            pd.DataFrame(datas).to_excel("static/"+file_path)

            if platform == "win32":
                # windows
                file_path = file_path.replace("/", "\\\\")
            
            if not file_path:
                return redirect('dashboard:dashboard')
            else:
                return self.render_to_json_response(file_path, safe=False)
            # download_file.download(
            #         request, 
            #         file_path,
            #         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            #     )

        except Exception as exc:
            return self.render_to_json_response({"error": _("An error has occurred...")}, safe=False)

        