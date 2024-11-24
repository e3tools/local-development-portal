from django.core.paginator import Paginator
from django.views import generic

from administrativelevels.models import Task, AdministrativeLevel
from cosomis.mixins import PageMixin
from django.utils.translation import gettext_lazy as _


class CddFunnelView(PageMixin, generic.ListView):
    template_name = "village_list.html"
    model = AdministrativeLevel
    title = _("CDD Funnel")
    paginate_by = 10

    def get_context_data(self, **kwargs):
        ctx = super(CddFunnelView, self).get_context_data(**kwargs)
        villages = list()
        admin_levels = self.object_list.filter(type=AdministrativeLevel.VILLAGE)
        paginator = Paginator(admin_levels, 25)  # Show 25 contacts per page.

        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)
        ctx['page_number'] = page_number
        ctx['page_obj'] = page_obj
        for admin_level in page_obj:
            uncompleted_tasks = 0
            for phase in admin_level.phases.all().order_by("order"):
                for activity in phase.activities.all().order_by("order"):
                    for task in activity.tasks.all().order_by("order"):
                        if task.status != Task.COMPLETED:
                            uncompleted_tasks = uncompleted_tasks + 1

            if uncompleted_tasks != 0:
                villages.append(
                    {
                        'name': admin_level.name,
                        'uncompleted_tasks': uncompleted_tasks,
                        'id': admin_level.id,
                    }
                )
        ctx['villages'] = villages
        return ctx

