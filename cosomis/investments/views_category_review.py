"""
Category review page (staff only): browse investments by category/sector,
correct misclassified ones, mark the rest as verified. The page is rendered
once, then every interaction swaps HTML fragments over HTMX.
"""

from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views import generic

from administrativelevels.models import Category, Sector
from cosomis.mixins import PageMixin
from . import category_review as review
from .models import Investment, InvestmentSectorChange

PAGE_SIZE = 20


class StaffRequiredMixin:
    """Staff accounts only (those allowed into the Django admin). Others get a
    404 so the page doesn't even reveal it exists."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not request.user.is_staff:
            raise Http404
        return super().dispatch(request, *args, **kwargs)


def results_context(params):
    """Context of the results fragment (_results.html) for a GET QueryDict."""
    filters = review.ReviewFilters(params)
    page_obj = Paginator(filters.queryset(), PAGE_SIZE).get_page(params.get("page"))
    querystring = params.copy()
    querystring.pop("page", None)
    return {
        "filters": filters,
        "page_obj": page_obj,
        "progress": filters.progress(),
        "unverified_ids": [
            inv.id for inv in page_obj if inv.category_verified_at is None
        ],
        "querystring": querystring.urlencode(),
    }


def _review_investment(pk):
    return get_object_or_404(
        review.with_card_data(
            Investment.objects.filter(
                investment_status__in=[Investment.PRIORITY, Investment.SUBPROJECT]
            )
        ),
        pk=pk,
    )


def _card(request, investment, state="default", change=None):
    return render(request, "investments/category_review/_card.html", {
        "inv": investment, "card_state": state, "change": change,
    })


class CategoryReviewView(StaffRequiredMixin, PageMixin, generic.TemplateView):
    template_name = "investments/category_review/page.html"
    title = _("Category review")

    def get_template_names(self):
        if self.request.htmx:
            return ["investments/category_review/_results.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(results_context(self.request.GET))
        if not self.request.htmx:
            context["categories"] = Category.objects.order_by("name")
            context["grouped_sectors"] = review.grouped_sectors()
        return context


class CategoryReviewSectorView(StaffRequiredMixin, generic.View):
    """GET: the inline correction form of a card. POST: apply the correction."""

    def get(self, request, pk):
        investment = _review_investment(pk)
        return render(request, "investments/category_review/_sector_form.html", {
            "inv": investment, "grouped_sectors": review.grouped_sectors(),
        })

    def post(self, request, pk):
        investment = _review_investment(pk)
        sector_id = request.POST.get("sector", "")
        sector = Sector.objects.filter(pk=sector_id).first() if sector_id.isdigit() else None
        if sector is None:
            return HttpResponseBadRequest(_("Choose a sub-category."))
        change = review.change_sector(investment, sector, request.user)
        if not request.htmx:
            return redirect("investments:category_review")
        return _card(
            request, _review_investment(pk),
            state="moved" if change else "default", change=change,
        )


class CategoryReviewUndoView(StaffRequiredMixin, generic.View):
    def post(self, request, pk):
        change = get_object_or_404(InvestmentSectorChange, pk=pk)
        try:
            review.undo_change(change, request.user)
        except review.StaleChangeError:
            state = "stale"
        else:
            state = "undone"
        if not request.htmx:
            return redirect("investments:category_review")
        return _card(request, _review_investment(change.investment_id), state=state)


class CategoryReviewHistoryView(StaffRequiredMixin, generic.View):
    def get(self, request, pk):
        investment = _review_investment(pk)
        return render(request, "investments/category_review/_history.html", {
            "inv": investment, "changes": review.history(investment),
        })


class CategoryReviewVerifyView(StaffRequiredMixin, generic.View):
    """Mark the investments shown on the current page as verified, then return
    the refreshed results for the same filters (carried in the querystring)."""

    def post(self, request):
        ids = [v for v in request.POST.getlist("investment") if v.isdigit()]
        review.mark_verified(ids, request.user)
        if not request.htmx:
            return redirect(reverse("investments:category_review") + "?" + request.GET.urlencode())
        return render(
            request, "investments/category_review/_results.html",
            results_context(request.GET),
        )
