from django.views import generic
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode
from django.utils.translation import gettext_lazy as _
from cosomis.mixins import PageMixin
from administrativelevels.models import AdministrativeLevel, Category
from .models import Investment


class IndexListView(PageMixin, generic.edit.BaseFormView, generic.ListView):
    template_name = 'investments/list.html'
    queryset = Investment.objects.filter(investment_status=Investment.PRIORITY)
    title = _('Investments')

    def post(self, request, *args, **kwargs):
        url = reverse('investments:home_investments')
        post_dict = request.POST.copy()
        post_dict.update(request.GET)
        post_dict.pop('csrfmiddlewaretoken')
        if 'reset-hidden' in post_dict and post_dict['reset-hidden'] == 'true':
            return redirect(url)

        for key, value in request.POST.items():
            if value == '':
                post_dict.pop(key)
        final_querystring = request.GET.copy()
        final_querystring.update(post_dict)
        if final_querystring:
            url = '{}?{}'.format(url, urlencode(final_querystring))
        return redirect(url)

    def get_context_data(self, **kwargs):
        adm_queryset = AdministrativeLevel.objects.all()
        kwargs['regions'] = adm_queryset.filter(type=AdministrativeLevel.REGION)
        kwargs['prefectures'] = adm_queryset.filter(type=AdministrativeLevel.PREFECTURE)
        kwargs['communes'] = adm_queryset.filter(type=AdministrativeLevel.COMMUNE)
        kwargs['cantons'] = adm_queryset.filter(type=AdministrativeLevel.CANTON)
        kwargs['villages'] = adm_queryset.filter(type=AdministrativeLevel.VILLAGE)

        kwargs['sectors'] = Category.objects.all()
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)
        return kwargs

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'region-filter' in self.request.GET and self.request.GET['region-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__id=self.request.GET['region-filter'],
                administrative_level__parent__parent__parent__type=AdministrativeLevel.REGION
            )
        if 'prefecture-filter' in self.request.GET and self.request.GET['prefecture-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__id=self.request.GET['prefecture-filter'],
                administrative_level__parent__parent__type=AdministrativeLevel.PREFECTURE
            )
        if 'commune-filter' in self.request.GET and self.request.GET['commune-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__id=self.request.GET['commune-filter'],
                administrative_level__parent__type=AdministrativeLevel.COMMUNE
            )
        if 'village-filter' in self.request.GET and self.request.GET['village-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__id=self.request.GET['village-filter'],
                administrative_level__type=AdministrativeLevel.VILLAGE
            )

        if 'sector-filter' in self.request.GET and self.request.GET['sector-filter'] not in ['', None]:
            queryset = queryset.filter(
                sector__id=self.request.GET['sector-filter']
            )

        return queryset
