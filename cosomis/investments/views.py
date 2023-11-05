from django.views import generic
from django.utils.translation import gettext_lazy as _
from cosomis.mixins import PageMixin
from .models import Investment


class IndexListView(PageMixin, generic.ListView):
    template_name = 'investments/list.html'
    queryset = Investment.objects.filter(investment_status=Investment.PRIORITY)
    title = _('Investments')
