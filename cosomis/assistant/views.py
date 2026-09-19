from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, resolve_url
from django.urls import reverse
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from assistant import agent, reports, scope
from assistant.models import Conversation, Message, Report
from cosomis.mixins import LoginRequiredApproveRequiredMixin, PageMixin

# Suggested questions, per role, in the portal's primary language.
SUGGESTIONS_ALL = [
    "Combien de villages sont profilés dans chaque région ?",
    "Quelles priorités « Eau & assainissement » ne sont pas encore financées dans le canton de Nano ?",
    "Résume le profil du village de Tamlou.",
    "Quels secteurs concentrent le plus de priorités de rang 1 ?",
    "Où en est le cycle de planification dans la préfecture de Kozah ?",
    "Prépare un rapport Word et PDF sur la région des Savanes.",
]
SUGGESTIONS_PARTNER = [
    "Où en sont mes paquets d'investissement ?",
    "Quels programmes mon organisation finance-t-elle ?",
]
SUGGESTIONS_STAFF = [
    "Combien de paquets attendent une validation ?",
    "Quels sous-projets ont moins de 30 % d'exécution physique ?",
]


def _active_conversation(user, create=False):
    conversation = Conversation.objects.filter(user=user, is_active=True).first()
    if conversation is None and create:
        conversation = Conversation.objects.create(user=user)
    return conversation


def panel_context(user):
    """Everything the drawer body needs: the active thread and the chips."""
    conversation = _active_conversation(user)
    return {
        "conversation": conversation,
        "chat_messages": conversation.messages.prefetch_related("reports") if conversation else [],
        "assistant_enabled": agent.is_configured(),
        "assistant_model": settings.ASSISTANT_MODEL,
        "role": scope.role_of(user),
        "suggestions": SUGGESTIONS_ALL + (
            SUGGESTIONS_STAFF if scope.is_staff_role(user) else SUGGESTIONS_PARTNER),
    }


def _home_with_drawer_open():
    """The assistant has no page of its own: it is a drawer on every page.

    Bookmarks and links to /assistant/ land on the home page with the drawer
    open (assistant.js reads the `assistant=open` query parameter).
    """
    return HttpResponseRedirect(f"{resolve_url(settings.LOGIN_REDIRECT_URL)}?assistant=open")


class ChatView(LoginRequiredApproveRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return _home_with_drawer_open()


class PanelView(LoginRequiredApproveRequiredMixin, PageMixin, TemplateView):
    """The drawer body, fetched by HTMX the first time the drawer is opened.

    Loading it lazily keeps the assistant off the critical path of every
    page: the drawer shell in layouts/base.html is static markup.
    """

    template_name = "assistant/_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(panel_context(self.request.user))
        return context


class SendView(LoginRequiredApproveRequiredMixin, View):
    """Answer one question. HTMX gets the two new bubbles; others get redirected."""

    def post(self, request, *args, **kwargs):
        is_htmx = bool(getattr(request, "htmx", False))
        question = (request.POST.get("question") or "").strip()[:2000]
        if not question:
            # 204 tells HTMX there is nothing to swap into the log.
            return HttpResponse(status=204) if is_htmx else _home_with_drawer_open()

        conversation = _active_conversation(request.user, create=True)
        if not conversation.title:
            conversation.title = question[:160]
            conversation.save(update_fields=["title"])
        history = list(conversation.messages.values_list("role", "content"))
        user_message = Message.objects.create(
            conversation=conversation, role=Message.USER, content=question)

        error = None
        assistant_message = None
        try:
            reply = agent.run_turn(request.user, history, question)
        except agent.AssistantUnavailable as exc:
            error = str(exc)
        else:
            assistant_message = Message.objects.create(
                conversation=conversation, role=Message.ASSISTANT,
                content=reply.answer, tool_trace=reply.tool_trace, model=reply.model,
                prompt_tokens=reply.prompt_tokens,
                completion_tokens=reply.completion_tokens)
            if reply.report_ids:
                # Written by the generate_report tool during this turn; the
                # download chips hang off the answer they came with.
                Report.objects.filter(id__in=reply.report_ids, user=request.user).update(
                    conversation=conversation, message=assistant_message)

        if not is_htmx:
            return _home_with_drawer_open()
        return render(request, "assistant/_exchange.html", {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "error": error,
        })


class NewConversationView(LoginRequiredApproveRequiredMixin, View):
    """Archive the active thread. HTMX gets a fresh panel (suggestions again)."""

    def post(self, request, *args, **kwargs):
        Conversation.objects.filter(user=request.user, is_active=True).update(is_active=False)
        if not getattr(request, "htmx", False):
            return _home_with_drawer_open()
        return render(request, "assistant/_panel.html", panel_context(request.user))


def _file_response(request, title, body, fmt):
    if fmt not in reports.FORMATS:
        raise Http404
    who = scope.describe(request.user)
    meta = _("%(program)s · %(date)s · %(name)s") % {
        "program": settings.PROGRAM_NAME,
        "date": formats.date_format(timezone.localdate(), "SHORT_DATE_FORMAT"),
        "name": who["name"],
    }
    footer = _("Generated from Local Development Portal data. This is not an official UCP statement.")
    try:
        data = reports.render(title, body, fmt, base_url=request.build_absolute_uri("/"),
                              meta=meta, footer=footer)
    except reports.ReportError:
        return HttpResponse(_("The file could not be generated."), status=500)
    response = HttpResponse(data, content_type=reports.content_type(fmt))
    response["Content-Disposition"] = f'attachment; filename="{reports.filename(title, fmt)}"'
    return response


class ReportDownloadView(LoginRequiredApproveRequiredMixin, View):
    """A report the assistant wrote, as Word or PDF. Owner only."""

    def get(self, request, token, fmt, *args, **kwargs):
        report = get_object_or_404(Report, token=token, user=request.user)
        return _file_response(request, report.title, report.body, fmt)


class MessageExportView(LoginRequiredApproveRequiredMixin, View):
    """Any assistant answer as Word or PDF, for the ones that were not a report."""

    def get(self, request, pk, fmt, *args, **kwargs):
        message = get_object_or_404(Message, pk=pk, role=Message.ASSISTANT,
                                    conversation__user=request.user)
        # Name the file after the question this answer replies to.
        question = Message.objects.filter(conversation=message.conversation, role=Message.USER,
                                          id__lt=message.id).last()
        title = (question.content[:160] if question else "") or _("Assistant answer")
        return _file_response(request, title, message.content, fmt)
