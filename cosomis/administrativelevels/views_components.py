from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.http import Http404
from functools import reduce

from cosomis.mixins import AJAXRequestMixin, JSONResponseMixin
from no_sql_client import NoSQLClient
from authentication.models import Facilitator
from administrativelevels.models import AdministrativeLevel
from administrativelevels.functions import get_cvds, get_datas_dict
from administrativelevels.libraries.functions import strip_accents
from subprojects.models import Subproject
from subprojects.serializers import SubprojectSerializer


class AdministrativeLevelMixin:
    administrative_level = None
    nsc = None

    def dispatch(self, request, pk: int, *args, **kwargs):
        try:
            self.administrative_level = AdministrativeLevel.objects.get(id=pk)
        except Exception:
             raise Http404
        self.nsc = NoSQLClient()
        return super().dispatch(request, *args, **kwargs)

class AdministrativeLevelOverviewComponent(AdministrativeLevelMixin, LoginRequiredMixin, generic.ListView):
    template_name = 'components/administrative_level_overview.html'
    context_object_name = 'datas'
    

    def get_results(self):

        population, nbr_menages, nbr_men, nbr_women, young, elderly, handicap = 0, 0, 0, 0, 0, 0, 0
        fermers_breeders, nbr_ethnic_minorities = 0, 0
        liste_minorities = []
        minorities = ""

        villages = []
        if self.administrative_level.type == "Canton":
            villages = self.administrative_level.administrativelevel_set.get_queryset()
        elif self.administrative_level.type == "Village":
            villages = [self.administrative_level]
            
        villages_cvds_ids = []
        _villages = []
        for v_c in villages:
            if v_c.cvd:
                _villages.append(v_c)
                if str(v_c.cvd.headquarters_village.id) not in villages_cvds_ids:
                    villages_cvds_ids.append(str(v_c.cvd.headquarters_village.id))

        length_villages_cvds_ids = len(villages_cvds_ids)
        count_villages_cvds = 0

        for f in Facilitator.objects.using('cdd').filter(develop_mode=False, training_mode=False):
            facilitator_db = self.nsc.get_db(f.no_sql_db_name)
            docs = facilitator_db.all_docs(include_docs=True)['rows']
            facilitator_doc = None
            for _doc in docs:
                doc = _doc.get('doc')
                if doc.get('type') == 'facilitator':
                    facilitator_doc = doc
                    break
            if facilitator_doc:
                cvds = get_cvds(facilitator_doc)
                for cvd in cvds:
                    village_id = cvd['village_id']
                    if village_id in villages_cvds_ids:
                        for _task in docs:
                            _task = _task.get('doc')
                            if _task.get('type') == 'task' and village_id == _task.get('administrative_level_id'):
                                form_response = _task.get("form_response")
                                if _task.get('sql_id') == 20 and form_response: #Etablissement du profil du village
                                    try:
                                        population += get_datas_dict(form_response, "population", 1)["populationTotaleDuVillage"]
                                    except Exception as exc:
                                        population = population
                                    
                                    try:
                                        nbr_menages += get_datas_dict(form_response, "generalitiesSurVillage", 1)["totalHouseHolds"]
                                    except Exception as exc:
                                        nbr_menages = nbr_menages
                                    
                                    try:
                                        nbr_men += get_datas_dict(form_response, "population", 1)["populationNombreDeHommes"]
                                    except Exception as exc:
                                        nbr_men = nbr_men
                                    
                                    try:
                                        nbr_women += get_datas_dict(form_response, "population", 1)["populationNombreDeFemmes"]
                                    except Exception as exc:
                                        nbr_women = nbr_women
                                    
                                    try:
                                        _ = get_datas_dict(form_response, "population", 1)["populationEthniqueMinoritaire"]
                                        _copy = (strip_accents(_).strip()).title()
                                        if _copy and _copy not in liste_minorities and _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-'):
                                            liste_minorities.append(_copy)
                                    except Exception as exc:
                                        _ = None
                        
                        count_villages_cvds += 1
                        
            if count_villages_cvds >= length_villages_cvds_ids:
                break
        liste_minorities = list(set(reduce(lambda a, b : a + ['Peuhl'] if b in ('Peulh', 'Peuhl', 'Paulh', 'Pauhl') else a + [b], liste_minorities , [])))
        
        return {
            "population": population, "nbr_menages": nbr_menages,
            "nbr_men": nbr_men, "nbr_women": nbr_women,
            "minorities": ', '.join(liste_minorities), 
            "nbr_ethnic_minorities": len(liste_minorities),
            "young": 0, "elderly": 0, "handicap": 0, "fermers_breeders": 0,
            "nbr_villages": len(villages)
        }
    
    def get_queryset(self):
        return self.get_results()


class AdministrativeLevelPrioritiesComponent(AdministrativeLevelMixin, AJAXRequestMixin, LoginRequiredMixin, JSONResponseMixin, generic.View):
    template_name = 'components/administrative_level_overview.html'
    context_object_name = 'datas'
    

    def get(self, request, *args, **kwargs):
        subprojects = []
        villages = []
        if self.administrative_level.type == "Canton":
            villages = self.administrative_level.administrativelevel_set.get_queryset()
            subprojects = list(Subproject.objects.filter(canton_id=self.administrative_level.id))
        elif self.administrative_level.type == "Village":
            villages = [self.administrative_level]

        for v in villages:
            subprojects += list(Subproject.objects.filter(location_subproject_realized_id=v.id))
        length_subprojects = len(subprojects)
        
        priorities_by_sector = {}
        summary_subprojects = {}
        
        for subp in subprojects:
            if not priorities_by_sector.get(subp.subproject_sector):
                priorities_by_sector[subp.subproject_sector] = {"number": 1, "percent": (1/length_subprojects)*100}
            else:
                priorities_by_sector[subp.subproject_sector]['number'] += 1
                priorities_by_sector[subp.subproject_sector]['percent'] = (priorities_by_sector[subp.subproject_sector]['number']/length_subprojects) * 100

            if not summary_subprojects.get(subp.full_title_of_approved_subproject):
                summary_subprojects[subp.full_title_of_approved_subproject] = {
                    'beneficiaries': (subp.direct_beneficiaries_men if subp.direct_beneficiaries_men else 0) + \
                    (subp.direct_beneficiaries_women if subp.direct_beneficiaries_women else 0)+ \
                    (subp.indirect_beneficiaries_men if subp.indirect_beneficiaries_men else 0)+ \
                    (subp.indirect_beneficiaries_women if subp.indirect_beneficiaries_women else 0),
                    'cost_unit': subp.estimated_cost, 'cost_total': subp.estimated_cost if subp.estimated_cost else 0,
                    'pk': subp.pk
                }
                if subp.canton:
                    summary_subprojects[subp.full_title_of_approved_subproject]['number_villages'] = (len(subp.list_of_villages_crossed_by_the_track_or_electrification.all()) if subp.list_of_villages_crossed_by_the_track_or_electrification else 0)
                else:
                    summary_subprojects[subp.full_title_of_approved_subproject]['cvds'] = [subp.cvd.id if subp.cvd else 0]
                    summary_subprojects[subp.full_title_of_approved_subproject]['number_villages'] = subp.location_subproject_realized.cvd.administrativelevel_set.get_queryset().count() if subp.location_subproject_realized.cvd else 0
            else:
                summary_subprojects[subp.full_title_of_approved_subproject]['beneficiaries'] += (subp.direct_beneficiaries_men if subp.direct_beneficiaries_men else 0) + \
                    (subp.direct_beneficiaries_women if subp.direct_beneficiaries_women else 0)+ \
                    (subp.indirect_beneficiaries_men if subp.indirect_beneficiaries_men else 0)+ \
                    (subp.indirect_beneficiaries_women if subp.indirect_beneficiaries_women else 0)
                summary_subprojects[subp.full_title_of_approved_subproject]['cost_total'] += subp.estimated_cost if subp.estimated_cost else 0
                
                if subp.canton:
                    summary_subprojects[subp.full_title_of_approved_subproject]['number_villages'] += (len(subp.list_of_villages_crossed_by_the_track_or_electrification.all()) if subp.list_of_villages_crossed_by_the_track_or_electrification else 0)
                else:
                    summary_subprojects[subp.full_title_of_approved_subproject]['cvds'].append(subp.cvd.id if subp.cvd else 0)
                    summary_subprojects[subp.full_title_of_approved_subproject]['number_villages'] += (subp.location_subproject_realized.cvd.administrativelevel_set.get_queryset().count() if subp.location_subproject_realized.cvd else 0)



        return self.render_to_json_response({
            'priorities_by_sector': priorities_by_sector,
            'subprojects': SubprojectSerializer(subprojects, many=True).data,
            'summary_subprojects': summary_subprojects
        }, safe=False)