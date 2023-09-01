from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.http import Http404
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import generic
from cosomis.mixins import PageMixin
from django.utils.translation import gettext_lazy as _
from django.core.paginator import Paginator
from django.db.models import Q


from financial.models import AdministrativeLevelAllocation
from usermanager.permissions import (
    EvaluatorPermissionRequiredMixin,
    )
from financial.forms import AdministrativeLevelAllocationForm
# Create your views here.



class AdministrativeLevelAllocationCreateView(PageMixin, LoginRequiredMixin, EvaluatorPermissionRequiredMixin, generic.CreateView):
    model = AdministrativeLevelAllocation
    template_name = 'allocation_add.html'
    context_object_name = 'allocation'
    title = _('Create Administrative level Allocation')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = AdministrativeLevelAllocationForm # specify the class form to be displayed
    
    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelAllocationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('financial:allocations_list')
        return super(AdministrativeLevelAllocationCreateView, self).get(request, *args, **kwargs)


class AdministrativeLevelAllocationUpdateView(PageMixin, LoginRequiredMixin, EvaluatorPermissionRequiredMixin, generic.UpdateView):
    model = AdministrativeLevelAllocation
    template_name = 'allocation_add.html'
    context_object_name = 'allocation'
    title = _('Update Administrative level Allocation')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]

    form_class = AdministrativeLevelAllocationForm # specify the class form to be displayed
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = AdministrativeLevelAllocationForm(instance=self.get_object())
        return context
    
    def post(self, request, *args, **kwargs):
        form = AdministrativeLevelAllocationForm(request.POST, instance=self.get_object())
        if form.is_valid():
            form.save()
            return redirect('financial:allocations_list')
        return super(AdministrativeLevelAllocationForm, self).get(request, *args, **kwargs)
    


class AdministrativeLevelAllocationsListView(PageMixin, LoginRequiredMixin, generic.ListView):
    """Display allocations list"""

    model = AdministrativeLevelAllocation
    queryset = []
    template_name = 'allocation_list.html'
    context_object_name = 'allocations'
    title = _('Allocations')
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
        _type = self.request.GET.get("type", "Canton")
        if search:
            if search == "All":
                ads = AdministrativeLevelAllocation.objects.filter(administrative_level__type__icontains=_type)
                return Paginator(ads, ads.count()).get_page(page_number)
            search = search.upper()
            return Paginator(AdministrativeLevelAllocation.objects.filter(
                Q(administrative_level__name__icontains=search) | 
                Q(project__name__icontains=search) | 
                Q(allocation_date__icontains=search) | 
                Q(description__icontains=search) | 
                Q(amount__icontains=search),
                administrative_level__type__icontains=_type
            ), 100).get_page(page_number)
        else:
            return Paginator(AdministrativeLevelAllocation.objects.filter(administrative_level__type=_type), 100).get_page(page_number)

        # return super().get_queryset()
    def get_context_data(self, **kwargs):
        ctx = super(AdministrativeLevelAllocationsListView, self).get_context_data(**kwargs)
        ctx['search'] = self.request.GET.get("search", None)
        ctx['type'] = self.request.GET.get("type", "Canton")
        return ctx
    

class AdministrativeLevelAllocationDetailView(PageMixin, LoginRequiredMixin, generic.DetailView):
    """Class to present the detail page of one allocations"""

    model = AdministrativeLevelAllocation
    template_name = 'alocation_detail.html'
    context_object_name = 'allocation'
    title = _('Village')
    active_level1 = 'financial'
    breadcrumb = [
        {
            'url': '',
            'title': title
        },
    ]
    