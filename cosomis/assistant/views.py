from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView

from assistant import agent, scope
from assistant.models import Conversation, Message
from cosomis.mixins import LoginRequiredApproveRequiredMixin, PageMixin

# Suggested questions, per role, in the portal's primary language.
SUGGESTIONS_ALL = [
    "Combien de villages sont profilés dans chaque région ?",
    "Quelles priorités « Eau & assainissement » ne sont pas encore financées dans le canton de Nano ?",
    "Résume le profil du village de Tamlou.",
    "Quels secteurs concentrent le plus de priorités de rang 1 ?",
    "Où en est le cycle de planification dans la préfecture de Kozah ?",
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


class ChatView(LoginRequiredApproveRequiredMixin, PageMixin, TemplateView):
    template_name = "assistant/chat.html"
    title = _("Assistant")
    active_level1 = "assistant"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        conversation = _active_conversation(self.request.user)
        context.update({
            "conversation": conversation,
            "chat_messages": conversation.messages.all() if conversation else [],
            "assistant_enabled": agent.is_configured(),
            "assistant_model": settings.ASSISTANT_MODEL,
            "role": scope.role_of(self.request.user),
            "suggestions": SUGGESTIONS_ALL + (
                SUGGESTIONS_STAFF if scope.is_staff_role(self.request.user)
                else SUGGESTIONS_PARTNER),
        })
        return context


class SendView(LoginRequiredApproveRequiredMixin, View):
    """Answer one question. HTMX gets the two new bubbles; others get redirected."""

    def post(self, request, *args, **kwargs):
        question = (request.POST.get("question") or "").strip()[:2000]
        if not question:
            return HttpResponseRedirect(reverse("assistant:chat"))

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

        if not getattr(request, "htmx", False):
            return HttpResponseRedirect(reverse("assistant:chat"))
        return render(request, "assistant/_exchange.html", {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "error": error,
        })


class NewConversationView(LoginRequiredApproveRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        Conversation.objects.filter(user=request.user, is_active=True).update(is_active=False)
        return HttpResponseRedirect(reverse("assistant:chat"))
