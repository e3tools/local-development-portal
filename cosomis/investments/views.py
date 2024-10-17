from datetime import datetime, timedelta
from django.conf import settings
from django.views import generic
from django.shortcuts import redirect
from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from urllib.parse import urlencode
from cosomis.mixins import PageMixin

from usermanager.models import User
from administrativelevels.models import AdministrativeLevel, Category, Sector, Project

from usermanager.permissions import IsInvestorMixin, IsModeratorMixin

from static.config.datatable import get_datatable_config

from .models import Investment, Package
from .forms import InvestmentsForm, PackageApprovalForm, UserApprovalForm


class ProfileTemplateView(IsInvestorMixin, PageMixin, generic.DetailView):
    template_name = "investments/profile.html"

    def get_object(self, queryset=None):
        """
        Return the object the view is displaying.

        Require `self.queryset` and a `pk` or `slug` argument in the URLconf.
        Subclasses can override this to return any object.
        """
        return self.request.user


class IndexListView(
    LoginRequiredMixin, PageMixin, generic.edit.BaseFormView, generic.ListView
):
    template_name = "investments/list.html"
    queryset = Investment.objects.filter(
        investment_status=Investment.PRIORITY,
        project_status=Investment.NOT_FUNDED
    )
    form_class = InvestmentsForm
    title = _("Investments")

    def post(self, request, *args, **kwargs):
        if "cart-submitted" in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        url = reverse("investments:home_investments")
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if (
                key in request.POST
                and value != request.POST[key]
                and request.POST[key] != ""
            ):
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop("csrfmiddlewaretoken")
        if "reset-hidden" in post_dict and post_dict["reset-hidden"] == "true":
            return redirect(url)

        for key, value in request.POST.items():
            if value == "":
                post_dict.pop(key)
        final_querystring.update(post_dict)
        if final_querystring:
            url = "{}?{}".format(url, urlencode(final_querystring))
        return redirect(url)

    def get_form_kwargs(self):
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
            "context": {"user": self.request.user},
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
        kwargs["regions"] = adm_queryset.filter(type=AdministrativeLevel.REGION)

        kwargs["prefectures"] = adm_queryset.filter(type=AdministrativeLevel.PREFECTURE)
        if "region-filter" in self.request.GET:
            kwargs["prefectures"] = kwargs["prefectures"].filter(
                parent__id=self.request.GET["region-filter"]
            )

        kwargs["communes"] = adm_queryset.filter(type=AdministrativeLevel.COMMUNE)
        if "prefecture-filter" in self.request.GET:
            kwargs["communes"] = kwargs["communes"].filter(
                parent__id=self.request.GET["prefecture-filter"]
            )

        kwargs["cantons"] = adm_queryset.filter(type=AdministrativeLevel.CANTON)
        if "commune-filter" in self.request.GET:
            kwargs["cantons"] = kwargs["cantons"].filter(
                parent__id=self.request.GET["commune-filter"]
            )

        kwargs["villages"] = adm_queryset.filter(type=AdministrativeLevel.VILLAGE)
        if "cantons-filter" in self.request.GET:
            kwargs["villages"] = kwargs["villages"].filter(
                parent__id=self.request.GET["cantons-filter"]
            )

        kwargs["categories"] = Category.objects.all()
        if "category-filter" in self.request.GET:
            kwargs["sectors"] = Sector.objects.filter(
                category=self.request.GET["category-filter"]
            )

        kwargs["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {
                "id": "endorsed_by_pastoralist",
                "name": _("Endorsed by ethnic minorities"),
            },
        ]

        kwargs["priorities"] = [
            {"id": 1, "name": _("Priority 1")},
            {"id": 2, "name": _("Priorities 1 and 2")},
            {"id": 3, "name": _("All priorities")}
        ]

        kwargs["query_strings"] = self.get_query_strings_context()
        kwargs["query_strings_raw"] = self.request.GET.copy()

        kwargs["selected_investments_data_querystring"] = '&'.join([key + '=' + value for key, value in kwargs["query_strings_raw"].items()])

        if self.request.user.organization is not None:
            kwargs["projects"] = self.request.user.organization.projects.all()
            kwargs['cart_project'] = Package.objects.get_active_cart(user=self.request.user).project

        kwargs.setdefault("view", self)
        if self.extra_context is not None:
            kwargs.update(self.extra_context)

        queryset = (
            kwargs["object_list"]
            if "object_list" in kwargs and kwargs["object_list"] is not None
            else self.object_list
        )
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

        context["datatable_config"] = get_datatable_config()
        context["datatable_config"]["responsive"] = "true"
        context["datatable_config"]["server-side"] = "true"
        context["datatable_config"]["processing"] = "true"
        context["datatable_config"]["searching"] = "false"
        context["datatable_config"]["ajax"] = self.request.scheme + '://' + self.request.get_host() + self.request.path + "ajax/datatable?format=datatables"
        context["datatable_config"]["columns"] = [
            {'data': 'select_input', 'name': 'select_input', 'searchable': 'false', 'orderable': 'false'},
            {'data': 'title'},
            {'data': 'administrative_level__type'},
            {'data': 'estimated_cost'},
            {'data': 'administrative_level__name'},
            {'data': 'administrative_level__parent__name'},
            {'data': 'administrative_level__parent__parent__name'},
            {'data': 'administrative_level__parent__parent__parent__name'},
            {'data': 'ranking'},
            {'data': 'population_priority', 'name': 'population_priority', 'searchable': 'false', 'orderable': 'false'},

        ]
        if len(kwargs["query_strings_raw"]) > 0 :
            context["datatable_config"]["ajax"] += "&" + kwargs["selected_investments_data_querystring"]
        context.update(kwargs)

        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        if "region-filter" in self.request.GET and self.request.GET[
            "region-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__parent__id=self.request.GET[
                    "region-filter"
                ],
                administrative_level__parent__parent__parent__parent__type=AdministrativeLevel.REGION,
            )
        if "prefecture-filter" in self.request.GET and self.request.GET[
            "prefecture-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__id=self.request.GET[
                    "prefecture-filter"
                ],
                administrative_level__parent__parent__parent__type=AdministrativeLevel.PREFECTURE,
            )
        if "commune-filter" in self.request.GET and self.request.GET[
            "commune-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__id=self.request.GET[
                    "commune-filter"
                ],
                administrative_level__parent__parent__type=AdministrativeLevel.COMMUNE,
            )
        if "canton-filter" in self.request.GET and self.request.GET[
            "canton-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__id=self.request.GET["canton-filter"],
                administrative_level__parent__type=AdministrativeLevel.CANTON,
            )
        if "village-filter" in self.request.GET and self.request.GET[
            "village-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__id=self.request.GET["village-filter"],
                administrative_level__type=AdministrativeLevel.VILLAGE,
            )

        if "sector-filter" in self.request.GET and self.request.GET[
            "sector-filter"
        ] not in ["", None]:
            queryset = queryset.filter(sector__id=self.request.GET["sector-filter"])
        if "category-filter" in self.request.GET and self.request.GET[
            "category-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                sector__category__id=self.request.GET["category-filter"]
            )

        if "subpopulation-filter" in self.request.GET and self.request.GET[
            "subpopulation-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                **{self.request.GET["subpopulation-filter"]: True}
            )

        if "climate-contribution-filter" in self.request.GET and self.request.GET[
            "climate-contribution-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                climate_contribution=self.request.GET["climate-contribution-filter"]
            )

        if "priorities-filter" in self.request.GET and self.request.GET[
            "priorities-filter"
        ] not in ["", None]:
            priorities = [1]
            if self.request.GET["priorities-filter"] == '2':
                priorities.append(2)
            elif self.request.GET["priorities-filter"] == '3':
                priorities.append(2)
                priorities.append(3)
            queryset = queryset.filter(
                ranking__in=priorities
            )

        if "is-funded-filter" in self.request.GET and self.request.GET[
            "is-funded-filter"
        ] not in ["", None]:
            if self.request.GET["is-funded-filter"] == 'true':
                queryset = queryset.exclude(project_status=Investment.NOT_FUNDED)
            else:
                queryset = queryset.exclude(
                    project_status=Investment.FUNDED
                )

        return queryset.none()

    def get_query_strings_context(self):
        resp = dict()
        for key, value in self.request.GET.items():
            if key == "region-filter":
                resp["Regions"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.REGION
                    ).values_list("name", flat=True)
                )
            if key == "prefecture-filter":
                resp["Prefectures"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.PREFECTURE
                    ).values_list("name", flat=True)
                )
            if key == "commune-filter":
                resp["Communes"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.COMMUNE
                    ).values_list("name", flat=True)
                )
            if key == "village-filter":
                resp["Villages"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.VILLAGE
                    ).values_list("name", flat=True)
                )

            if key == "category-filter":
                resp["Categories"] = ", ".join(
                    Category.objects.filter(
                        id__in=[int(value)],
                    ).values_list("name", flat=True)
                )
            if key == "sector-filter":
                resp["Sectors"] = ", ".join(
                    Sector.objects.filter(
                        id__in=[int(value)],
                    ).values_list("name", flat=True)
                )
            if key == "subpopulation-filter":
                resp["Subpopulations"] = " ".join(value.split("_"))

            if key == "climate-contribution-filter":
                resp["Climate contribution"] = _("Yes") if value == "True" else _("No")

            if key == "priorities-filter":
                if value == "1":
                    resp["Priorities"] = _('Priority 1')
                elif value == "2":
                    resp["Priorities"] = _('Priorities 1 and 2')
                else:
                    resp["Priorities"] = _('All priorities')
        return resp

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse("investments:cart")


class PackageDetailView(IsInvestorMixin, PageMixin, generic.DetailView):
    template_name = "investments/package.html"
    queryset = Package.objects.all()

    def get_queryset(self):
        queryset = super(PackageDetailView, self).get_queryset()
        return queryset.filter(project__organization=self.request.user.organization)

    def get_context_data(self, **kwargs):
        context = super(PackageDetailView, self).get_context_data(**kwargs)
        context["datatable_config"] = get_datatable_config()
        context["datatable_config"]["responsive"] = "true"
        context["datatable_config"]["columnDefs"] = [
            {"responsivePriority": 1, "targets": 0},
            {"responsivePriority": 2, "targets": 1},
            {"responsivePriority": 3, "targets": 2},
            {"responsivePriority": 4, "targets": 3},
            {"responsivePriority": 5, "targets": 4},
            {"responsivePriority": 6, "targets": 5},
            {"responsivePriority": 7, "targets": 6},
            {"responsivePriority": 9, "targets": 7},
            {"responsivePriority": 8, "targets": 8},
        ]
        sectors = list()
        categories = list()
        context['total_funding'] = 0

        for inv in context["object"].funded_investments.all():
            sectors.append(inv.sector)
            categories.append(inv.sector.category)
            context['total_funding'] += inv.estimated_cost

        context['title'] = context["object"].status

        context["sectors"] = dict.fromkeys(sectors)
        context["categories"] = dict.fromkeys(categories)

        context['cart_project'] = Package.objects.get_active_cart(user=self.request.user).project
        context['projects'] = self.request.user.organization.projects.all()

        return context


class CartView(IsInvestorMixin, PageMixin, generic.DetailView):
    template_name = "investments/cart.html"
    queryset = Package.objects.filter(status=Package.PENDING_APPROVAL)
    title = _("Your package")

    def post(self, request, *args, **kwargs):
        package = Package.objects.get_active_cart(user=self.request.user)
        if not package.project:
            package.project = Project.objects.get(id=request.POST["project"], organization=request.user.organization)
            package.save()
            return redirect(reverse('investments:cart'))
        else:
            obj = self.get_object()
            if "remove-from-cart" in request.POST:
                investment = Investment.objects.get(pk=request.POST["remove-from-cart"])
                package.funded_investments.remove(investment)
                messages.add_message(request, messages.SUCCESS, _("Investment removed from cart."))
                return redirect(reverse('investments:cart'))
            elif "clear-package-input" in request.POST:
                obj.funded_investments.clear()
                obj.project = None
                obj.save()
            else:
                obj.status = Package.PENDING_APPROVAL
                obj.save()
                messages.add_message(request, messages.SUCCESS, _("Package submitted."))
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
        context["datatable_config"] = get_datatable_config()
        context["datatable_config"]["responsive"] = "true"
        context["datatable_config"]["columnDefs"] = [
            {"responsivePriority": 1, "targets": 0},
            {"responsivePriority": 2, "targets": 1},
            {"responsivePriority": 3, "targets": 2},
            {"responsivePriority": 4, "targets": 3},
            {"responsivePriority": 5, "targets": 4},
            {"responsivePriority": 6, "targets": 5},
            {"responsivePriority": 7, "targets": 6},
            {"responsivePriority": 10, "targets": 7},
            {"responsivePriority": 9, "targets": 8},
            {"responsivePriority": 8, "targets": 9},
        ]
        sectors = list()
        categories = list()
        context['total_funding'] = 0

        for inv in context["object"].funded_investments.all():
            sectors.append(inv.sector)
            categories.append(inv.sector.category)
            context['total_funding'] += inv.estimated_cost

        context["sectors"] = dict.fromkeys(sectors)
        context["categories"] = dict.fromkeys(categories)

        context['cart_project'] = Package.objects.get_active_cart(user=self.request.user).project
        context['projects'] = self.request.user.organization.projects.all()

        return super(CartView, self).get_context_data(**context)


class ModeratorApprovalsListView(IsModeratorMixin, PageMixin, generic.ListView):
    template_name = "investments/moderator/approvals_list.html"
    package_model = Package
    user_model = User
    ordering = ["-status", "-created_date"]
    allow_empty = True
    object_list = None
    title = _("Welcome, Moderator!")

    def post(self, request, *args, **kwargs):
        form = UserApprovalForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(
                self.request,
                messages.SUCCESS,
                message=form.success_message,
                extra_tags=messages.DEFAULT_TAGS[messages.SUCCESS],
            )
        return self.get(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        self.package_list = self.get_package_queryset()
        self.user_list = self.get_user_queryset()

        context = self.get_context_data()
        return self.render_to_response(context)

    def get_context_data(self, *, object_list=None, **kwargs):
        """Get the context for this view."""
        overdue_date = datetime.now() - timedelta(days=settings.MAX_RESPONSE_DAYS)
        package_queryset = self.package_list
        user_queryset = self.user_list
        context = {
            "paginator": None,
            "page_obj": None,
            "is_paginated": False,
            "package_list": package_queryset,
            "packages_overdue": package_queryset.filter(updated_date__lt=overdue_date),
            "user_list": user_queryset,
            "users_overdue": user_queryset.filter(date_joined__lt=overdue_date),
        }
        context.update(kwargs)

        context.setdefault("title", self.title)
        context.setdefault("active_level1", self.active_level1)
        context.setdefault("active_level2", self.active_level2)
        context.setdefault("breadcrumb", self.breadcrumb)
        context.setdefault("form_mixin", self.form_mixin)

        context.setdefault("view", self)
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context

    def get_package_queryset(self):
        queryset = self.package_model._default_manager.exclude(
            status=Package.PENDING_SUBMISSION
        )
        ordering = self.get_ordering()
        if ordering:
            if isinstance(ordering, str):
                ordering = (ordering,)
            queryset = queryset.order_by(*ordering)

        return queryset

    def get_user_queryset(self):
        queryset = self.user_model._default_manager.filter(
            is_approved=None, is_moderator=False
        ).order_by("date_joined")
        return queryset


class ModeratorPackageReviewView(
    IsModeratorMixin, PageMixin, generic.FormView, generic.DetailView
):
    template_name = "investments/moderator/package_review.html"
    form_class = PackageApprovalForm
    queryset = Package.objects.filter(status=Package.PENDING_APPROVAL)
    pk_url_kwarg = "package"
    title = _("Investment Package Review")

    def post(self, request, *args, **kwargs):
        if "investments-from" in request.POST:
            form = self.get_form()
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        url = reverse(
            "investments:package_review", kwargs={"package": self.get_object().id}
        )
        final_querystring = request.GET.copy()

        for key, value in request.GET.items():
            if (
                key in request.POST
                and value != request.POST[key]
                and request.POST[key] != ""
            ):
                final_querystring.pop(key)

        post_dict = request.POST.copy()
        post_dict.update(final_querystring)
        post_dict.pop("csrfmiddlewaretoken")
        if "reset-hidden" in post_dict and post_dict["reset-hidden"] == "true":
            return redirect(url)

        for key, value in request.POST.items():
            if value == "":
                post_dict.pop(key)
        final_querystring.update(post_dict)
        if final_querystring:
            url = "{}?{}".format(url, urlencode(final_querystring))
        return redirect(url)

    def get_context_data(self, **kwargs):
        context = {}
        self.object = self.get_object()
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()

        if self.object:
            context["object"] = self.object
            context_object_name = self.get_context_object_name(self.object)
            if context_object_name:
                context[context_object_name] = self.object
        context.update(kwargs)
        context.update(self.get_filters_context())
        context.update(self.get_investment_list())
        return super().get_context_data(**context)

    def get_form_kwargs(self):
        """Return the keyword arguments for instantiating the form."""
        kwargs = {
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
            "context": {"user": self.request.user},
        }

        post_data = self.request.POST.copy()
        post_data["package"] = self.get_object()

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": post_data,
                    "files": self.request.FILES,
                }
            )
        return kwargs

    def get_filters_context(self):
        kwargs = dict()
        adm_queryset = AdministrativeLevel.objects.all()
        kwargs["regions"] = adm_queryset.filter(type=AdministrativeLevel.REGION)

        kwargs["prefectures"] = adm_queryset.filter(type=AdministrativeLevel.PREFECTURE)
        if "region-filter" in self.request.GET:
            kwargs["prefectures"] = kwargs["prefectures"].filter(
                parent__id=self.request.GET["region-filter"]
            )

        kwargs["communes"] = adm_queryset.filter(type=AdministrativeLevel.COMMUNE)
        if "prefecture-filter" in self.request.GET:
            kwargs["communes"] = kwargs["communes"].filter(
                parent__id=self.request.GET["prefecture-filter"]
            )

        kwargs["cantons"] = adm_queryset.filter(type=AdministrativeLevel.CANTON)
        if "commune-filter" in self.request.GET:
            kwargs["cantons"] = kwargs["cantons"].filter(
                parent__id=self.request.GET["commune-filter"]
            )

        kwargs["villages"] = adm_queryset.filter(type=AdministrativeLevel.VILLAGE)
        if "cantons-filter" in self.request.GET:
            kwargs["villages"] = kwargs["villages"].filter(
                parent__id=self.request.GET["cantons-filter"]
            )

        kwargs["query_strings"] = self.get_query_strings_context()
        kwargs["query_strings_raw"] = self.request.GET.copy()

        kwargs["categories"] = Category.objects.all()
        if "category-filter" in self.request.GET:
            kwargs["sectors"] = Sector.objects.filter(
                category=self.request.GET["category-filter"]
            )
        kwargs["subpopulations"] = [
            {"id": "endorsed_by_youth", "name": _("Endorsed by youth")},
            {"id": "endorsed_by_women", "name": _("Endorsed by women")},
            {"id": "endorsed_by_agriculturist", "name": _("Endorsed by agriculturist")},
            {"id": "endorsed_by_pastoralist", "name": _("Endorsed by pastoralist")},
        ]
        return kwargs

    def get_query_strings_context(self):
        resp = dict()
        for key, value in self.request.GET.items():
            if key == "region-filter":
                resp["Regions"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.REGION
                    ).values_list("name", flat=True)
                )
            if key == "prefecture-filter":
                resp["Prefectures"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.PREFECTURE
                    ).values_list("name", flat=True)
                )
            if key == "commune-filter":
                resp["Communes"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.COMMUNE
                    ).values_list("name", flat=True)
                )
            if key == "village-filter":
                resp["Villages"] = ", ".join(
                    AdministrativeLevel.objects.filter(
                        id__in=[int(value)], type=AdministrativeLevel.VILLAGE
                    ).values_list("name", flat=True)
                )

            if key == "category-filter":
                resp["Categories"] = ", ".join(
                    Category.objects.filter(
                        id__in=[int(value)],
                    ).values_list("name", flat=True)
                )
            if key == "sector-filter":
                resp["Sectors"] = ", ".join(
                    Sector.objects.filter(
                        id__in=[int(value)],
                    ).values_list("name", flat=True)
                )
            if key == "subpopulation-filter":
                resp["Subpopulations"] = " ".join(value.split("_"))
        return resp

    def get_investment_list(self):
        queryset = self.object.funded_investments.all()
        if "region-filter" in self.request.GET and self.request.GET[
            "region-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__parent__id=self.request.GET[
                    "region-filter"
                ],
                administrative_level__parent__parent__parent__parent__type=AdministrativeLevel.REGION,
            )
        if "prefecture-filter" in self.request.GET and self.request.GET[
            "prefecture-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__parent__id=self.request.GET[
                    "prefecture-filter"
                ],
                administrative_level__parent__parent__parent__type=AdministrativeLevel.PREFECTURE,
            )
        if "commune-filter" in self.request.GET and self.request.GET[
            "commune-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__parent__id=self.request.GET[
                    "commune-filter"
                ],
                administrative_level__parent__parent__type=AdministrativeLevel.COMMUNE,
            )
        if "canton-filter" in self.request.GET and self.request.GET[
            "canton-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__parent__id=self.request.GET["canton-filter"],
                administrative_level__parent__type=AdministrativeLevel.CANTON,
            )
        if "village-filter" in self.request.GET and self.request.GET[
            "village-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                administrative_level__id=self.request.GET["village-filter"],
                administrative_level__type=AdministrativeLevel.VILLAGE,
            )

        if "sector-filter" in self.request.GET and self.request.GET[
            "sector-filter"
        ] not in ["", None]:
            queryset = queryset.filter(sector__id=self.request.GET["sector-filter"])
        if "category-filter" in self.request.GET and self.request.GET[
            "category-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                sector__category__id=self.request.GET["category-filter"]
            )

        if "subpopulation-filter" in self.request.GET and self.request.GET[
            "subpopulation-filter"
        ] not in ["", None]:
            queryset = queryset.filter(
                **{self.request.GET["subpopulation-filter"]: True}
            )

        return {"investments": queryset}

    def form_valid(self, form):
        """If the form is valid, redirect to the supplied URL."""
        form.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            message="Package approved successfully.",
            extra_tags=messages.DEFAULT_TAGS[messages.SUCCESS],
        )
        return reverse("investments:notifications")
