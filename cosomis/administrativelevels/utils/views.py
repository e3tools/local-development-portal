import csv
from datetime import datetime
import json
import geojson
import os
import subprocess
from django.db.models import Subquery
from django.views import generic
from django.http import HttpResponse
from openpyxl import Workbook
from rest_framework import generics, response

from cosomis.mixins import AJAXRequestMixin, JSONResponseMixin, LoginRequiredApproveRequiredMixin
from administrativelevels.models import AdministrativeLevel, Phase, Activity, Task, Sector, GeoSegment


class GetAdministrativeLevelForCVDByADLView(AJAXRequestMixin, LoginRequiredApproveRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        adl_id = request.GET.get('administrative_level_id')

        objects = AdministrativeLevel.objects.filter(id=int(adl_id))
        d = []
        if objects:
            obj = objects.first()
            if obj.cvd:
                d = [{'id': elt.id, 'name': elt.name} for elt in obj.cvd.get_villages()]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)


class GetChoicesForNextAdministrativeLevelNoConditionView(AJAXRequestMixin, LoginRequiredApproveRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')

        data = AdministrativeLevel.objects.filter(parent_id=int(parent_id))

        d = [{'id': elt.id, 'name': elt.name, 'disabled': self.is_empty(elt)} for elt in data]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)

    def is_empty(self, village):
        phases = village.phases.all().count()
        attachements = village.attachments.all().count()
        return phases == 0 and attachements == 0 and village.total_population ==0
    

class GetChoicesForNextAdministrativeLevelView(AJAXRequestMixin, LoginRequiredApproveRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        parent_id = request.GET.get('parent_id')
        geographical_unit_id = request.GET.get('geographical_unit_id', None)

        data = AdministrativeLevel.objects.filter(parent_id=int(parent_id))

        d = [{'id': elt.id, 'name': elt.name} for elt in data if((not elt.geographical_unit) or (elt.geographical_unit and geographical_unit_id and elt.geographical_unit.id == int(geographical_unit_id)))]

        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)


class GetChoicesAdministrativeLevelByGeographicalUnitView(AJAXRequestMixin, LoginRequiredApproveRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        geographical_unit_id = request.GET.get('geographical_unit_id')
        cvd_id = request.GET.get('cvd_id', None)

        data = AdministrativeLevel.objects.filter(geographical_unit=int(geographical_unit_id))

        d = [{'id': elt.id, 'name': elt.name} for elt in data if((not elt.cvd) or (elt.cvd and cvd_id and elt.cvd.id == int(cvd_id)))]
        
        return self.render_to_json_response(sorted(d, key=lambda o: o['name']), safe=False)
    

class GetAncestorAdministrativeLevelsView(AJAXRequestMixin, LoginRequiredApproveRequiredMixin, JSONResponseMixin, generic.View):
    def get(self, request, *args, **kwargs):
        administrative_id = request.GET.get('administrative_id', None)
        ancestors = []
        try:
            ancestors.insert(0, str(AdministrativeLevel.objects.get(id=int(administrative_id)).parent.id))
        except Exception as exc:
            pass

        return self.render_to_json_response(ancestors, safe=False)


class TaskDetailAjaxView(generic.TemplateView):
    template_name = 'administrative_level/detail/task_detail.html'  # Define your template location

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        # Get task id from URL parameters
        task_id = self.kwargs.get('pk', None)
        task = Task.objects.filter(id=task_id).first()

        if task:
            # Ensure dict_form_responses is a valid JSON string or dict
            # Adding task details to the context
            context['task'] = {
                'name': task.name,
                'description': task.description,
                'status': task.status,
                'task': {
                    'form_response': task.form_responses,  # This is now a properly formatted JSON string or a dict
                    'form': task.form,  # This is now a properly formatted JSON string or a dict
                    'attachments_ids': ','.join([str(attachment.id) for attachment in task.attachments.all()]),
                    'attachments': [{
                        "name": attachment.name,
                        "type": attachment.type,
                        "order": attachment.order,
                        "attachment": {
                            "uri": attachment.url
                        }
                    } for attachment in task.attachments.all()],  # This is now a properly formatted JSON string or a dict
                },  # This is now a properly formatted JSON string or a dict
            }

            for attachment in task.attachments.all():
                print('----')
                print(attachment.id)
                print(attachment.name)
                print(attachment.type)
                print(attachment.order)
                print(attachment.url)
                print('----')

        else:
            # Optionally handle the case where the task is not found
            context['error'] = 'Task not found'

        return context


class FillAttachmentSelectFilters(generics.GenericAPIView):
    """
    Region -> Prefecture -> Commune -> Canton -> Village
    """

    def post(self, request, *args, **kwargs):
        select_type = request.POST['type']
        child_qs = list()
        if select_type == 'region':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.REGION)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.PREFECTURE)
        elif select_type == 'prefecture':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.PREFECTURE)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.COMMUNE)
        elif select_type == 'commune':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.COMMUNE)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.CANTON)
        elif select_type == 'canton':
            parent_qs = AdministrativeLevel.objects.filter(id=request.POST['value'], type=AdministrativeLevel.CANTON)
            child_qs = AdministrativeLevel.objects.filter(parent=Subquery(parent_qs.values('id')), type=AdministrativeLevel.VILLAGE)
        elif select_type == 'village':
            parent_obj = AdministrativeLevel.objects.get(id=request.POST['value'], type=AdministrativeLevel.VILLAGE)
            child_qs = Phase.objects.filter(village=parent_obj)
        elif select_type == 'phase':
            # parent_obj = Phase.objects.filter(id=request.POST['value'])
            child_qs = Activity.objects.filter(phase__name=request.POST['value'])
        elif select_type == 'activity':
            # parent_obj = Activity.objects.get(id=request.POST['value'])
            child_qs = Task.objects.filter(activity__name=request.POST['value'])

        return response.Response({
            'values': [{'id': child.id, 'name': child.name} for child in child_qs]
        })


# class SectorCodesCSVView(LoginRequiredApproveRequiredMixin, generic.View):
#     queryset = Sector.objects.all()
#
#     def get(self, *args, **kwargs):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="sectors_codes.csv"'
#
#         writer = csv.writer(response)
#
#         writer.writerow(['id', 'name', 'category'])
#
#         rows = self.queryset.values_list('id', 'name', 'category__name')
#         for row in rows:
#             writer.writerow(row)
#
#         return response


class SectorCodesXLSXView(LoginRequiredApproveRequiredMixin, generic.View):
    queryset = Sector.objects.all()

    def get(self, *args, **kwargs):
        # Création d'un nouveau classeur Excel
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sector Codes"

        # Ajout des en-têtes
        headers = ['ID', 'Name', 'Category']
        sheet.append(headers)

        # Récupération et ajout des données
        rows = self.queryset.values_list('id', 'name', 'category__name')
        for row in rows:
            sheet.append([col if col is not None else '' for col in row])

        # Préparation de la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="sectors_codes_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        )

        # Sauvegarde du classeur dans la réponse
        workbook.save(response)
        return response


# class VillagesCodesCSVView(LoginRequiredApproveRequiredMixin, generic.View):
#     queryset = AdministrativeLevel.objects.filter(type=AdministrativeLevel.VILLAGE)
#
#     def get(self, *args, **kwargs):
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="administrative_level_codes.csv"'
#
#         writer = csv.writer(response)
#
#         writer.writerow(['id', 'region', 'prefecture', 'commune', 'canton', 'village'])
#
#         rows = self.queryset.values_list('id', 'parent__parent__parent__parent__name', 'parent__parent__parent__name',
#                                          'parent__parent__name', 'parent__name', 'name')
#         for row in rows:
#             writer.writerow(row)
#
#         return response


class VillagesCodesXLSXView(LoginRequiredApproveRequiredMixin, generic.View):
    queryset = AdministrativeLevel.objects.filter(
        type=AdministrativeLevel.VILLAGE
    ).select_related(
        'parent__parent__parent__parent', 'parent__parent__parent', 'parent__parent', 'parent'
    )

    def get(self, *args, **kwargs):
        # Création d'un nouveau classeur Excel
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Villages Codes"

        # Ajout des en-têtes
        headers = ['ID', 'Région', 'Préfecture', 'Commune', 'Canton', 'Village']
        sheet.append(headers)

        # Récupération et écriture des données
        rows = self.queryset.values_list(
            'id',
            'parent__parent__parent__parent__name',
            'parent__parent__parent__name',
            'parent__parent__name',
            'parent__name',
            'name'
        )
        for row in rows:
            sheet.append([col if col is not None else '' for col in row])

        # Préparation de la réponse HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="villages_codes_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        )

        # Sauvegarde du classeur dans la réponse
        workbook.save(response)
        return response


class InitializeVillageCoordinatesView(LoginRequiredApproveRequiredMixin, generic.TemplateView):
    template_name = 'village_coordinates.html'
    file_path = 'administrativelevels/utils/Village Coords RGPH-5.csv'

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def post(self, request, *args, **kwargs):
        # Region > Prefecture > Commune > Canton > Village

        villages = list()
        counter = 0

        with open(self.file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)

            header = next(csv_reader)
            print("Header:")
            print(header)

            for row in csv_reader:
                village = AdministrativeLevel.objects.filter(
                    parent__parent__parent__parent__name__iexact=row[2],
                    parent__parent__parent__name__iexact=row[4],
                    parent__parent__name__iexact=row[6],
                    parent__name__iexact=row[8],
                    name__iexact=row[12],
                    type=AdministrativeLevel.VILLAGE
                )
                if village:
                    counter += 1
                    village = village[0]
                    village.longitude = row[16]
                    village.latitude = row[17]
                    village.code_loc = row[0]
                    villages.append(village)

            AdministrativeLevel.objects.bulk_update(villages, fields=['longitude', 'latitude', 'code_loc'])
            self.extra_context= {
                'villages_affected': counter
            }
        return self.get(request, *args, **kwargs)

    def load_geojson(self):
        # Replace 'your_file.geojson' with the path to your GeoJSON file
        with open('administrativelevels/utils/grid_clusterID.geojson', 'r') as file:
            data = geojson.load(file)

        # Print the GeoJSON data
        print(len(data['features']))

        geo_segments = list()

        # Accessing specific features (e.g., list of features)
        for feature in data['features']:
            if feature['properties']['Country'] == 'Togo':
                coordinates = GeoSegment.sort_coordinates(feature['geometry']['coordinates'][0])
                geo_segments.append(GeoSegment(
                    longitude_northwest=coordinates[0][0],
                    latitude_northwest=coordinates[0][1],
                    longitude_northeast=coordinates[1][0],
                    latitude_northeast=coordinates[1][1],
                    longitude_southeast=coordinates[2][0],
                    latitude_southeast=coordinates[2][1],
                    longitude_southwest=coordinates[3][0],
                    latitude_southwest=coordinates[3][1],
                    cluster_id=feature['properties']['ClusterID'],
                    country=feature['properties']['Country'],
                    lc_gencat_20=feature['properties']['LC_gencat_20'],
                    region=feature['properties']['Region'],
                    acled_bexrem_sum=feature['properties']['acled_BExRem_sum'],
                    acled_civvio_sum=feature['properties']['acled_CivVio_sum'],
                    acled_riodem_sum=feature['properties']['acled_RioDem_sum'],
                    fatal_sum=feature['properties']['fatal_sum'],
                    grid_id=feature['properties']['gridID'],
                    popplace_travel=feature['properties']['popPlace_travel'],
                    population_20=feature['properties']['population_20'],
                    population_2000_diff=feature['properties']['population_2000_diff'],
                    pr_avg_2020_diff=feature['properties']['pr_avg_2020_diff'],
                    road_len=feature['properties']['roadLen'],
                    tmmx_avg_2020_diff=feature['properties']['tmmx_avg_2020_diff'],
                ))

        GeoSegment.objects.bulk_create(geo_segments)

    def create_json(self):
        """
        [2] REGION
        [4] PREFECTURE
        [6] COMMUNE
        [8] CANTON/QUARTIER
        [12] VILLAGE/QUARTIER
        [16] LONGITUDE
        [17] LATITUDE
        """
        # Region > Prefecture > Commune > Canton > Village

        data = {'regions': []}

        with open(self.file_path, mode='r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)

            header = next(csv_reader)
            print("Header:")
            print(header)

            for row in csv_reader:
                region_flag = False
                for region in data['regions']:
                    if row[2] == region['name']:
                        region_flag = True
                        region_node = region
                if not region_flag:
                    region_node = {
                        'name': row[2],
                        'bd_id': None,
                        'is_in_file': True,
                        'type': AdministrativeLevel.REGION,
                        'children': [],
                    }
                    data['regions'].append(region_node)

                prefecture_flag = False
                for prefecture in region_node['children']:
                    if row[4] == prefecture['name']:
                        prefecture_flag = True
                        prefecture_node = prefecture
                if not prefecture_flag:
                    prefecture_node = {
                        'name': row[4],
                        'bd_id': None,
                        'is_in_file': True,
                        'type': AdministrativeLevel.PREFECTURE,
                        'children': [],
                    }
                    region_node['children'].append(prefecture_node)

                commune_flag = False
                for commune in prefecture_node['children']:
                    if row[6] == commune['name']:
                        commune_flag = True
                        commune_node = commune
                if not commune_flag:
                    commune_node = {
                        'name': row[6],
                        'bd_id': None,
                        'is_in_file': True,
                        'type': AdministrativeLevel.COMMUNE,
                        'children': [],
                    }
                    prefecture_node['children'].append(commune_node)

                canton_flag = False
                for canton in commune_node['children']:
                    if row[8] == canton['name']:
                        canton_flag = True
                        canton_node = canton
                if not canton_flag:
                    canton_node = {
                        'name': row[8],
                        'bd_id': None,
                        'is_in_file': True,
                        'type': AdministrativeLevel.CANTON,
                        'children': [],
                    }
                    commune_node['children'].append(canton_node)

                village_flag = False
                for village in commune_node['children']:
                    if row[12] == village['name']:
                        village_flag = True
                        village_node = village
                if not village_flag:
                    village_node = {
                        'name': row[12],
                        'bd_id': None,
                        'is_in_file': True,
                        'type': AdministrativeLevel.VILLAGE,
                    }
                    canton_node['children'].append(village_node)


        region_qs = AdministrativeLevel.objects.filter(type=AdministrativeLevel.REGION)
        for region in region_qs:
            bd_region_flag = False
            for json_region in data['regions']:
                if region.name == json_region['name']:
                    bd_region_flag = True
                    json_region['bd_id'] = region.id

                    prefecture_qs = region.children.all()
                    for prefecture in prefecture_qs:
                        bd_prefecture_flag = False
                        for json_prefecture in json_region['children']:
                            if prefecture.name == json_prefecture['name']:
                                bd_prefecture_flag = True
                                json_prefecture['bd_id'] = prefecture.id

                                commune_qs = prefecture.children.all()
                                for commune in commune_qs:
                                    bd_commune_flag = False
                                    for json_commune in json_prefecture['children']:
                                        if commune.name == json_commune['name']:
                                            bd_commune_flag = True
                                            json_commune['bd_id'] = commune.id

                                            canton_qs = commune.children.all()
                                            for canton in canton_qs:
                                                bd_canton_flag = False
                                                for json_canton in json_commune['children']:
                                                    if canton.name == json_canton['name']:
                                                        bd_canton_flag = True
                                                        json_canton['bd_id'] = canton.id

                                                        village_qs = canton.children.all()
                                                        for village in village_qs:
                                                            db_bd_village_flag = False
                                                            for json_village in json_canton['children']:
                                                                if village.name == json_village['name']:
                                                                    db_bd_village_flag = True
                                                                    json_village['bd_id'] = village.id

                                                            if db_bd_village_flag:
                                                                village_node = {
                                                                    'name': village.name,
                                                                    'bd_id': village.id,
                                                                    'is_in_file': False,
                                                                    'type': AdministrativeLevel.VILLAGE,
                                                                }
                                                                json_commune['children'].append(village_node)

                                                if not bd_canton_flag:
                                                    canton_node = {
                                                        'name': canton.name,
                                                        'bd_id': canton.id,
                                                        'is_in_file': False,
                                                        'type': AdministrativeLevel.CANTON,
                                                        'children': self.map_children(canton),
                                                    }
                                                    json_commune['children'].append(canton_node)
                                    if not bd_commune_flag:
                                        commune_node = {
                                            'name': commune.name,
                                            'bd_id': commune.id,
                                            'is_in_file': False,
                                            'type': AdministrativeLevel.COMMUNE,
                                            'children': self.map_children(commune),
                                        }
                                        json_prefecture['children'].append(commune_node)
                        if not bd_prefecture_flag:
                            prefecture_node = {
                                'name': prefecture.name,
                                'bd_id': prefecture.id,
                                'is_in_file': False,
                                'type': AdministrativeLevel.PREFECTURE,
                                'children': self.map_children(prefecture),
                            }
                            json_region['children'].append(prefecture_node)
            if not bd_region_flag:
                region_node = {
                    'name': region.name,
                    'bd_id': region.id,
                    'is_in_file': False,
                    'type': AdministrativeLevel.REGION,
                    'children': self.map_children(region),
                }
                data['regions'].append(region_node)


        with open('administrativelevels/utils/congruence.json', 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        return

    def map_children(self, parent):
        if parent.type != AdministrativeLevel.CANTON:
            return [{
                'name': node.name,
                'bd_id': node.id,
                'is_in_file': False,
                'type': node.type,
                'children': self.map_children(node),
            } for node in parent.children.all()]
        else:
            return [{
                'name': node.name,
                'bd_id': node.id,
                'is_in_file': False,
                'type': node.type,
            } for node in parent.children.all()]

    def convert_shapefiles_to_geojson(self, root_directory):
        # Traverse all subdirectories
        for subdir, _, files in os.walk(root_directory):
            for file in files:
                # Process only .shp files
                if file.endswith(".shp"):
                    shp_path = os.path.join(subdir, file)
                    geojson_path = os.path.splitext(shp_path)[0] + ".json"  # Naming the GeoJSON file

                    # Use ogr2ogr command from GDAL to convert to GeoJSON
                    command = [
                        "ogr2ogr", "-f", "GeoJSON", geojson_path, shp_path
                    ]

                    try:
                        # Run the command to convert the shapefile
                        subprocess.run(command, check=True)
                        print(f"Converted {shp_path} to {geojson_path}")
                    except subprocess.CalledProcessError as e:
                        print(f"Error converting {shp_path}: {e}")
