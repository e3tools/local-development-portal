"""
Development plans shown on the village and canton profiles.

A plan is the file uploaded under a given label on a planning task, once that
task is validated in CouchDB. A village or canton runs one planning cycle per
project, so it has at most one plan per project: the most recently validated
copy.
"""
from django.db.models import F

from investments.models import Attachment

# Uploaded on the PAV task of the fourth village meeting, worded the same by
# every project.
VILLAGE_PLAN_TASK_NAMES = ("Elaboration du plan d'action villageois (PAV)",)
VILLAGE_PLAN_ATTACHMENT_NAME = "Télecharger le document du plan d'actions finalisé"

# Uploaded on the cantonal arbitration task, which each project words
# differently. Every headquarters village's cycle carries a copy of that task.
CANTON_PLAN_TASK_NAMES = (
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage, la sélection des sous - projets "
    "à financer et l'affection des ressources par sous - projet",  # COSO
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage, la sélection des sous - projets "
    "à financer et l'affectation des ressources par sous - projet",  # FA-COSO
    "Appui au CCD dans  l'analyse des PAV des villages, l'arbitrage des priorités pour la rédaction du PDC.",  # PURS
)
CANTON_PLAN_ATTACHMENT_NAME = "Télecharger le document du plan d'actions cantonales finalisé"


def latest_development_plans(villages, task_names, attachment_name) -> list:
    """
    Returns the latest validated plan of each project among the villages'
    tasks, ordered by project name. Each Attachment carries project_name and
    validated_on (the task's validation date).
    """
    plans = (
        Attachment.objects.filter(
            name=attachment_name,
            task__name__in=task_names,
            task__validated=True,
            task__activity__phase__village__in=villages,
        )
        .exclude(url__startswith='file:')  # still on the tablet, never uploaded
        .annotate(
            project_name=F('task__activity__phase__project__name'),
            validated_on=F('task__date_validated'),
        )
        .order_by(F('task__date_validated').desc(nulls_last=True), '-id')
        .only('id', 'url')
    )
    latest = {}
    for plan in plans:
        latest.setdefault(plan.project_name, plan)
    return sorted(latest.values(), key=lambda plan: plan.project_name or '')


def village_development_plans(village) -> list:
    return latest_development_plans([village], VILLAGE_PLAN_TASK_NAMES, VILLAGE_PLAN_ATTACHMENT_NAME)


def canton_development_plans(villages) -> list:
    return latest_development_plans(villages, CANTON_PLAN_TASK_NAMES, CANTON_PLAN_ATTACHMENT_NAME)
