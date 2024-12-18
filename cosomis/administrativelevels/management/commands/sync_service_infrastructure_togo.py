from django.core.management.base import BaseCommand
from administrativelevels.models import AdministrativeLevel, Task


class Command(BaseCommand):
    help = 'Syncronize the services and infrastructure from village planning cycle to administrative level'

    def handle(self, *args, **options):
        task_qs = Task.objects.filter(order=4, activity__order=2, activity__phase__order=1)
        for task in task_qs:
            if len(task.form_responses) > 2:
                if 'equipementEtInfrastructures' in task.form_responses[7]:
                    resp = task.form_responses[7]['equipementEtInfrastructures']
                    admlvl_infrastructure = dict()
                    if 'sante' in resp:
                        admlvl_infrastructure['health_care'] = {
                            "dispensaire": True if resp['sante']['santeDispensaire'] == "Oui" else False,
                            "peripheral_care_unit": True if resp['sante']['santeUSP'] == "Oui" else False,
                            "specialized_medical_centers": True if resp['sante']['santeCMS'] == "Oui" else False,
                            "clinique": True if resp['sante']['santeClinique'] == "Oui" else False,
                            "other": None if resp['sante']['santeAutre'] == 'RAS' else resp['sante']['santeAutre']
                        }
                    if 'ecoles' in resp:
                        admlvl_infrastructure['education'] = {
                            'preschool': True if resp['ecoles']['ecoleprescolaire'] == 'Oui' else False,
                            'primary_school': True if resp['ecoles']['ecolePrimaire'] == 'Oui' else False,
                            'high_school': True if resp['ecoles']['ecoleLycee'] == 'Oui' else False,
                            'college': True if resp['ecoles']['ecoleCollege'] == 'Oui' else False,
                            'other': None if resp['ecoles']['ecoleAutre'] == 'RAS' else resp['ecoles']['ecoleAutre']
                        }
                    if 'religieu' in resp:
                        admlvl_infrastructure['religion'] = {
                            'church': True if resp['religieu']["religieuEglise"] == "Oui" else False,
                            "mosque": True if resp['religieu']["religieuMosquee"] == "Oui" else False,
                            "other": None if resp['religieu']["religeuAutres"] == 'RAS' else resp['religieu']["religeuAutres"]
                        }
                    if 'infrastDeMarches' in resp:
                        admlvl_infrastructure['markets'] = {
                            'shed': True if resp['infrastDeMarches']["hangar"] == "Oui" else False,
                        }
                    if 'infrastRoutieres' in resp:
                        admlvl_infrastructure['markets'] = {
                            'track': True if resp['infrastRoutieres']["piste"] == "Oui" else False,
                        }
                    for key in resp:
                        if key not in ['sante', 'ecoles', 'religieu', 'infrastDeMarches', 'infrastRoutieres']:
                            print('´{}´ not mapped. Please review the algorith to include it.'.format(key))
                    village = task.activity.phase.village
                    village.infrastructure = admlvl_infrastructure
                    village.save()


