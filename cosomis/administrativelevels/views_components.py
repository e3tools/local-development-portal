from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views import generic
from django.http import Http404
from functools import reduce
import re as re_module

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
        average_distance_from_nearest_town = None
        liste_minorities, languages, religions, climate_datas, infras  = [], [], [], [], []
        attachments = []
        attachment_image_principal = {}
        minorities = ""
        cvds_infos = []
        facilitator, date_identified_priorities, date_submission = None, None, None
        last_task_completed = {
            "phase_name": "VISITES PREALABLES",
            "activity_name": "Réunion cantonale",
            "name": "Introduction et présentation de l'AC par l'AADB lors de la première réunion cantonale",
            "task_order": 1
        }

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
                facilitator = facilitator_doc
                cvds = get_cvds(facilitator_doc)
                for cvd in cvds:
                    cvd_infos = {'cvd': cvd}
                    village_id = cvd['village_id']
                    if village_id in villages_cvds_ids:
                        for _task in docs:
                            _task = _task.get('doc')
                            if _task.get('type') == 'task' and village_id == _task.get('administrative_level_id'):
                                form_response = _task.get("form_response")

                                if ((not last_task_completed and _task.get('completed')) or (
                                        last_task_completed and _task.get('completed') and _task.get('task_order') > last_task_completed.get('task_order') 
                                    )):
                                    last_task_completed = _task

                                _attachments = [i for i in (_task.get("attachments") if _task.get("attachments") else []) if i.get("attachment")]
                                for i_attr in range(len(_attachments)):
                                    try:
                                        _attachments[i_attr]["date_de_la_reunion"] = form_response[0]["dateDeLaReunion"]
                                    except:
                                        try:
                                            _attachments[i_attr]["date_de_la_reunion"] = form_response[0]["DateDeLaFormation"]
                                        except:
                                            try:
                                                _attachments[i_attr]["date_de_la_reunion"] = form_response[0]["dateDeSeance"]
                                            except:
                                                try:
                                                    _attachments[i_attr]["date_de_la_reunion"] = form_response[0]["dateDeSoumission"]
                                                except:
                                                    try:
                                                        _attachments[i_attr]["date_de_la_reunion"] = form_response[0]["dateDeSensibilisation"]
                                                    except:
                                                        try:
                                                            _attachments[i_attr]["date_de_la_reunion"] = get_datas_dict(form_response, "dateDeLaReunion", 1)
                                                        except:
                                                            _attachments[i_attr]["date_de_la_reunion"] = None
                                if form_response:
                                    if _task.get('sql_id') == 20: #Etablissement du profil du village
                                        try:
                                            _ = get_datas_dict(form_response, "population", 1)["populationTotaleDuVillage"]
                                            population += _
                                            cvd_infos['population'] = _
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
                                            if _:
                                                _copy = (strip_accents(_).strip()).title().replace('-', ' ')
                                                if _copy and _copy not in liste_minorities and _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-', '0', 'Pas De Minorite'):
                                                    liste_minorities += [i.strip() for i in re_module.split('[,;/]|Et', _copy)]
                                        except Exception as exc:
                                            pass
                                        
                                        try:
                                            ethnicite = get_datas_dict(form_response, "Ethnicité", 1)
                                            _l = []
                                            if ethnicite:
                                                for ethnic in ethnicite:
                                                    if ethnic and ethnic.get("NomEthnicité"):
                                                        _copy = (strip_accents(ethnic["NomEthnicité"]).strip()).title().replace('-', ' ')
                                                        if _copy and _copy not in _l and _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-', '0', 'Pas De Minorite'):
                                                            _l += [i.strip() for i in re_module.split('[,;/]|Et', _copy)]
                                            languages += _l
                                            if 'Autres' in _l:
                                                _l.remove('Autres')
                                                _l.append('Autres')
                                            cvd_infos['languages'] = _l
                                        except Exception as exc:
                                            pass

                                        try:
                                            _religions = get_datas_dict(form_response, "Religion", 1)
                                            _l = []
                                            if _religions:
                                                for religion in _religions:
                                                    if religion and religion.get("NomReligion"):
                                                        _copy = (strip_accents(religion["NomReligion"]).strip()).title().replace('-', ' ')
                                                        if _copy and _copy not in _l and _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-', '0', 'Pas De Minorite'):
                                                            _l += [i.strip() for i in re_module.split('[,;/]|Et', _copy)]
                                            religions += _l
                                            if 'Autres' in _l:
                                                _l.remove('Autres')
                                                _l.append('Autres')
                                            cvd_infos['religions'] = _l
                                        except Exception as exc:
                                            pass

                                        try:
                                            climatiques = get_datas_dict(form_response, "climatiques", 1)
                                            if climatiques:
                                                for climatique in climatiques:
                                                    if climatique and climatique.get("aléas"):
                                                        _copy = (strip_accents(climatique["aléas"]).strip()).title().replace('-', ' ')
                                                        if _copy and _copy not in climatiques and _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-', '0', 'Pas De Minorite'):
                                                            climate_datas += [i.strip() for i in re_module.split('[,;/]|Et', _copy)]
                                        except Exception as exc:
                                            pass

                                        try:
                                            _ = get_datas_dict(form_response, "distanceAgglomeration", 1)
                                            if average_distance_from_nearest_town == None:
                                                average_distance_from_nearest_town = _
                                            elif _ and _ < average_distance_from_nearest_town:
                                                average_distance_from_nearest_town = _
                                        except Exception as exc:
                                            pass
                                        
                                        try:
                                            _ = get_datas_dict(form_response, "equipementEtInfrastructures", 1)
                                            if _:
                                                for key, value in _.items():
                                                    for k, v in value.items():
                                                        if v:
                                                            if v == "Oui":
                                                                _copy = _task['form'][7]['options']['fields']['equipementEtInfrastructures']['fields'][key]['fields'][k]['label']
                                                                if _copy not in infras:
                                                                    infras.append(_copy)
                                                            elif v != "Non":
                                                                _copy = (strip_accents(v).strip()).title().replace('-', ' ')
                                                                if _copy not in ('Nean', 'Neant', 'Oo', 'X', 'Non', '-', '0', 'Pas De Minorite') and _copy not in infras:
                                                                    infras += [i.strip() for i in re_module.split('[,;/]|Et', _copy)]
                                        except Exception as exc:
                                            pass
                                    if _task.get('sql_id') == 41: #Présenter les activités de la journée
                                        try:
                                            date_identified_priorities = form_response[0]["dateDeLaReunion"]
                                        except:
                                            pass
                                    if _task.get('sql_id') == 51: #Présenter les activités de la journée
                                        try:
                                            date_submission = form_response[0]["dateDeSoumission"]
                                        except:
                                            pass

                                    attachments += _attachments   
                        count_villages_cvds += 1
                        cvds_infos.append(cvd_infos)


            if count_villages_cvds >= length_villages_cvds_ids:
                break
        peuls = ('Peulh', 'Peuhl', 'Paulh', 'Pauhl', 'Peuls', 'Peul', 'Peul...', 'Peul.')
        liste_minorities = list(set(reduce(lambda a, b : a + ['Peuhl'] if b in peuls else a + [b], liste_minorities , [])))
        languages = list(set(reduce(lambda a, b : a + ['Peuhl'] if b in peuls else a + [b], languages , [])))
        religions = list(set(reduce(lambda a, b : (a + ['Christianisme'] if 'Chr' in b else (
            a + ['Musulmane'] if 'Musulm' in b else (a + ['Animisme'] if 'Animis' in b else (
                a + ['Islam'] if 'Islam' in b else a + [b]
            ))
        )), religions , [])))
        climate_datas = list(set(climate_datas))

        if 'Autres' in liste_minorities:
            liste_minorities.remove('Autres')
            liste_minorities.append('Autres')
        if 'Autres' in languages:
            languages.remove('Autres')
            languages.append('Autres')
        if 'Autres' in religions:
            religions.remove('Autres')
            religions.append('Autres')
        if 'Autres' in climate_datas:
            climate_datas.remove('Autres')
            climate_datas.append('Autres')
        
        for attach in attachments:
            if attach and attach.get("type") and "image" in attach.get("type") and attach.get("attachment"):
                attachment_image_principal = attach

        return {
            "population": population, "nbr_menages": nbr_menages,
            "nbr_men": nbr_men, "nbr_women": nbr_women,
            "minorities": ', '.join(liste_minorities), 
            "nbr_ethnic_minorities": len(liste_minorities),
            "young": 0, "elderly": 0, "handicap": 0, "fermers_breeders": 0,
            "nbr_villages": len(villages),
            "languages": languages, "religions": religions, "climate_datas": climate_datas,
            "average_distance_from_nearest_town": average_distance_from_nearest_town, "infras": infras,
            "cvds_infos": cvds_infos, "attachment_image_principal": attachment_image_principal,
            "attachments": attachments, "exists_at_least_attachment": len(attachments) != 0,
            "object": self.administrative_level, "last_task_completed": last_task_completed,
            "facilitator": facilitator, "date_identified_priorities": date_identified_priorities,
            "date_submission": date_submission
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