from django.views import generic
from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Subquery, Sum
from urllib.parse import urlencode
from cosomis.mixins import PageMixin
from administrativelevels.models import AdministrativeLevel
from static.config.datatable import get_datatable_config
from .models import Investment, Package, Category, Sector
from .forms import InvestmentsForm


class ProfileTemplateView(LoginRequiredMixin, PageMixin, generic.DetailView):
    template_name = 'investments/profile.html'
    queryset = User.objects.all()
    extra_context = {
        'datatable_config': get_datatable_config()
    }

    def get_context_data(self, **kwargs):
        context = super(ProfileTemplateView, self).get_context_data(**kwargs)
        context['packages'] = self.request.user.packages.exclude(status=Package.REJECTED).order_by('created_date')
        inv_ids = list()
        for package in context['packages']:
            inv_ids += package.funded_investments.all().values_list('id', flat=True)
        context['investments'] = Investment.objects.filter(id__in=inv_ids)
        try:
            context['organization'] = self.request.user.user_conf.get().organization
        except self.request.user.user_conf.model.DoesNotExist as e:
            context['organization'] = None

        if context['organization'] is not None:
            user_qs = context['organization'].user_conf.all().values_list('user__id')
            investments_qs = Investment.objects.filter(packages__user__id__in=Subquery(user_qs))
            context['organization'].total_investments = investments_qs.count()
            context['organization'].total_investments_amount = investments_qs.aggregate(Sum('estimated_cost'))['estimated_cost__sum']
        return context

    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.

        Require `self.queryset` and a `pk` or `slug` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        return self.request.user


class IndexListView(LoginRequiredMixin, PageMixin, generic.edit.BaseFormView, generic.ListView):
    template_name = 'investments/list.html'
    queryset = Investment.objects.filter(investment_status=Investment.PRIORITY)
    form_class = InvestmentsForm
    title = _('Investments')

    def post(self, request, *args, **kwargs):
        if 'investments' in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        url = reverse('investments:home_investments')
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if key in request.POST and value != request.POST[key] and request.POST[key] != '':
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

    def get_form_kwargs(self):
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
            "context": {
                "user": self.request.user
            },
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_context_data(self, **kwargs):
        adm_queryset = AdministrativeLevel.objects.all()
        kwargs['regions'] = adm_queryset.filter(type=AdministrativeLevel.REGION)

        kwargs['prefectures'] = adm_queryset.filter(type=AdministrativeLevel.PREFECTURE)
        if 'region-filter' in self.request.GET:
            kwargs['prefectures'] = kwargs['prefectures'].filter(parent__id=self.request.GET['region-filter'])

        kwargs['communes'] = adm_queryset.filter(type=AdministrativeLevel.COMMUNE)
        if 'prefecture-filter' in self.request.GET:
            kwargs['communes'] = kwargs['communes'].filter(parent__id=self.request.GET['prefecture-filter'])

        kwargs['cantons'] = adm_queryset.filter(type=AdministrativeLevel.CANTON)
        if 'commune-filter' in self.request.GET:
            kwargs['cantons'] = kwargs['cantons'].filter(parent__id=self.request.GET['commune-filter'])

        kwargs['villages'] = adm_queryset.filter(type=AdministrativeLevel.VILLAGE)
        if 'cantons-filter' in self.request.GET:
            kwargs['villages'] = kwargs['villages'].filter(parent__id=self.request.GET['cantons-filter'])

        kwargs['query_strings'] = self.get_query_strings_context()
        kwargs['query_strings_raw'] = self.request.GET.copy()

        kwargs['categories'] = Category.objects.all()
        if 'category-filter' in self.request.GET:
            kwargs['sectors'] = Sector.objects.filter(category=self.request.GET['category-filter'])
        kwargs['subpopulations'] = [
            {
                'id': 'endorsed_by_youth',
                'name': _('Endorsed by youth')
            },
            {
                'id': 'endorsed_by_women',
                'name': _('Endorsed by women')
            },
            {
                'id': 'endorsed_by_agriculturist',
                'name': _('Endorsed by agriculturist')
            },
            {
                'id': 'endorsed_by_pastoralist',
                'name': _('Endorsed by pastoralist')
            },
        ]
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

        context['datatable_config'] = get_datatable_config()
        context['datatable_config']['responsive'] = 'true'
        context['datatable_config']['columnDefs'] = [
                {'responsivePriority': 1, 'targets': 0},
                {'responsivePriority': 2, 'targets': 1},
                {'responsivePriority': 3, 'targets': 2},
                {'responsivePriority': 4, 'targets': 3},
                {'responsivePriority': 5, 'targets': 4},
                {'responsivePriority': 6, 'targets': 5},
                {'responsivePriority': 7, 'targets': 6},
                {'responsivePriority': 8, 'targets': 7},
                {'responsivePriority': 9, 'targets': 8},
                {'responsivePriority': 10, 'targets': 9}
            ]
        context.update(kwargs)

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'region-filter' in self.request.GET and self.request.GET['region-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__parent__id=self.request.GET['region-filter'],
                administrative_level__parent__parent__parent__parent__type=AdministrativeLevel.REGION
            )
        if 'prefecture-filter' in self.request.GET and self.request.GET['prefecture-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__id=self.request.GET['prefecture-filter'],
                administrative_level__parent__parent__parent__type=AdministrativeLevel.PREFECTURE
            )
        if 'commune-filter' in self.request.GET and self.request.GET['commune-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__id=self.request.GET['commune-filter'],
                administrative_level__parent__parent__type=AdministrativeLevel.COMMUNE
            )
        if 'canton-filter' in self.request.GET and self.request.GET['canton-filter'] not in ['', None]:
            queryset = queryset.filter(
                administrative_level__parent__id=self.request.GET['canton-filter'],
                administrative_level__parent__type=AdministrativeLevel.CANTON
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
        if 'category-filter' in self.request.GET and self.request.GET['category-filter'] not in ['', None]:
            queryset = queryset.filter(
                sector__category__id=self.request.GET['category-filter']
            )

        if 'subpopulation-filter' in self.request.GET and self.request.GET['subpopulation-filter'] not in ['', None]:
            queryset = queryset.filter(
                **{self.request.GET['subpopulation-filter']: True}
            )

        return queryset

    def get_query_strings_context(self):
        resp = dict()
        for key, value in self.request.GET.items():
            if key == 'region-filter':
                resp['Regions'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=[int(value)],
                    type=AdministrativeLevel.REGION
                ).values_list('name', flat=True))
            if key == 'prefecture-filter':
                resp['Prefectures'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=[int(value)],
                    type=AdministrativeLevel.PREFECTURE
                ).values_list('name', flat=True))
            if key == 'commune-filter':
                resp['Communes'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=[int(value)],
                    type=AdministrativeLevel.COMMUNE
                ).values_list('name', flat=True))
            if key == 'village-filter':
                resp['Villages'] = ', '.join(AdministrativeLevel.objects.filter(
                    id__in=[int(value)],
                    type=AdministrativeLevel.VILLAGE
                ).values_list('name', flat=True))

            if key == 'category-filter':
                resp['Categories'] = ', '.join(Category.objects.filter(
                    id__in=[int(value)],
                ).values_list('name', flat=True))
            if key == 'sector-filter':
                resp['Sectors'] = ', '.join(Sector.objects.filter(
                    id__in=[int(value)],
                ).values_list('name', flat=True))
            if key == 'subpopulation-filter':
                resp['Subpopulations'] = ' '.join(value.split('_'))
        return resp

    def get_success_url(self):
        return reverse('investments:cart')


class CartView(LoginRequiredMixin, PageMixin, generic.DetailView):
    template_name = 'investments/cart.html'
    queryset = Package.objects.filter(status=Package.PENDING_APPROVAL)
    title = _('Your cart')

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = Package.PENDING_APPROVAL
        obj.save()
        return redirect(reverse('investments:home_investments'))

    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.

        Require `self.queryset` and a `pk` or `slug` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        # Use a custom queryset if provided; this is required for subclasses
        # like DateDetailView
        if queryset is None:
            queryset = self.get_queryset()

        try:
            # Get the single item from the filtered queryset
            obj = queryset.get_active_cart(self.request.user)
        except queryset.model.DoesNotExist:
            raise Http404(
                _("No %(verbose_name)s found matching the query")
                % {"verbose_name": queryset.model._meta.verbose_name}
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super(CartView, self).get_context_data(**kwargs)
        context['datatable_config'] = get_datatable_config()
        sectors = list()
        categories = list()

        for inv in context["object"].funded_investments.all():
            sectors.append(inv.sector)
            categories.append(inv.sector.category)

        kwargs['sectors'] = dict.fromkeys(sectors)
        kwargs['categories'] = dict.fromkeys(categories)
        return super(CartView, self).get_context_data(**kwargs)
