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
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if key in request.POST:
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop('csrfmiddlewaretoken')
        if 'reset-hidden' in post_dict and post_dict['reset-hidden'] == 'true':
            return redirect(url)

        for key, value in request.POST.items():
            if value == '':
                post_dict.pop(key)
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
        kwargs['query_strings'] = self.get_query_strings_context()

        kwargs['sectors'] = Category.objects.all()
        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)

        queryset = kwargs['object_list'] if 'object_list' in kwargs and kwargs['object_list'] is not None else self.object_list
        page_size = self.get_paginate_by(queryset)
        context_object_name = self.get_context_object_name(queryset)
        if page_size:
            paginator, page, queryset, is_paginated = self.paginate_queryset(
                queryset, page_size
            )
            context = {
                "paginator": paginator,
                "page_obj": page,
                "is_paginated": is_paginated,
                "object_list": queryset,
            }
        else:
            context = {
                "paginator": None,
                "page_obj": None,
                "is_paginated": False,
                "object_list": queryset,
            }
        if context_object_name is not None:
            context[context_object_name] = queryset
        context.update(kwargs)

        return context

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

    def get_query_strings_context(self):
        resp = dict()
        for key, value in self.request.GET.items():
            if key == 'region-filter':
                resp['Regions'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=value,
                    type=AdministrativeLevel.REGION
                ).values_list('name', flat=True))
            if key == 'prefecture-filter':
                resp['Prefectures'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=value,
                    type=AdministrativeLevel.PREFECTURE
                ).values_list('name', flat=True))
            if key == 'commune-filter':
                resp['Communes'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=value,
                    type=AdministrativeLevel.COMMUNE
                ).values_list('name', flat=True))
            if key == 'village-filter':
                resp['Villages'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=value,
                    type=AdministrativeLevel.VILLAGE
                ).values_list('name', flat=True))

            if key == 'sector-filter':
                resp['Sectors'] = ', '.join(Category.objects.filter(
                    id__in=value,
                ).values_list('name', flat=True))
        return resp
