from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import generic
from cosomis.mixins import PageMixin
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q


from financial.models.financial import Disbursement
from usermanager.permissions import (
    AccountantPermissionRequiredMixin,
    )
from financial.forms import DisbursementForm
# Create your views here.




class DisbursementCreateView(PageMixin, LoginRequiredMixin, AccountantPermissionRequiredMixin, generic.CreateView):
    model = Disbursement
    template_name = 'disbursement_add.html'
    context_object_name = 'disbursement'
    title = _('Register a disbursement')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = DisbursementForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form_mixin:
            context['form'] = self.form_mixin
        else:
            context['form'] = DisbursementForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = DisbursementForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('financial:financials')
        self.form_mixin = form
        return super(DisbursementCreateView, self).get(request, *args, **kwargs)


class DisbursementUpdateView(PageMixin, LoginRequiredMixin, AccountantPermissionRequiredMixin, generic.UpdateView):
    model = Disbursement
    template_name = 'disbursement_add.html'
    context_object_name = 'disbursement'
    title = _('Update disbursement')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = DisbursementForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.form_mixin:
            context['form'] = self.form_mixin
        else:
            context['form'] = DisbursementForm(instance=self.get_object())
        return context
    
    
    def post(self, request, *args, **kwargs):
        form = DisbursementForm(request.POST, instance=self.get_object())
        if form.is_valid():
            form.save()
            return redirect('financial:financials')
        self.form_mixin = form
        return super(DisbursementUpdateView, self).get(request, *args, **kwargs)
    


class DisbursementsListView(PageMixin, LoginRequiredMixin, generic.ListView):
    """Display bank Disbursements list"""

    model = Disbursement
    queryset = []
    template_name = 'disbursement_list.html'
    context_object_name = 'disbursements'
    title = _('Disbursements')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    def get_queryset(self):
        search = self.request.GET.get("search", None)
        page_number = self.request.GET.get("page", None)
        if search:
            if search == "All":
                ads = Disbursement.objects.filter()
                return Paginator(ads, ads.count()).get_page(page_number)
            search = search.upper()
            return Paginator(Disbursement.objects.filter(
                Q(project__name__icontains=search) | 
                Q(transfer_date__icontains=search) | 
                Q(description__icontains=search) | 
                Q(motif__icontains=search) | 
                Q(amount_transferred__icontains=search)
            ), 100).get_page(page_number)
        else:
            return Paginator(Disbursement.objects.filter(), 100).get_page(page_number)

        # return super().get_queryset()
    def get_context_data(self, **kwargs):
        ctx = super(DisbursementsListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        ctx['type'] = self.request.GET.get("type", "cvd")
        return ctx
    

class DisbursementDetailView(PageMixin, LoginRequiredMixin, generic.DetailView):
    """Class to present the detail page of one Disbursement"""

    model = Disbursement
    template_name = 'disbursement_detail.html'
    context_object_name = 'disbursement'
    title = _('Disbursement')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    