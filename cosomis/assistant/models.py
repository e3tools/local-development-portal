import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse

from cosomis.models_base import BaseModel


class Conversation(BaseModel):
    """One chat thread. A user has at most one active thread at a time."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="assistant_conversations")
    title = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_date"]

    def __str__(self):
        return self.title or f"Conversation {self.pk}"


class Message(BaseModel):
    """A user question or the assistant's answer, with the tool calls it used.

    Kept for audit and for building an evaluation set: every answer records
    which tools ran with which arguments, and what the call cost.
    """

    USER = "user"
    ASSISTANT = "assistant"
    ROLES = ((USER, "User"), (ASSISTANT, "Assistant"))

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,
                                     related_name="messages")
    role = models.CharField(max_length=10, choices=ROLES)
    content = models.TextField()
    tool_trace = models.JSONField(null=True, blank=True)
    model = models.CharField(max_length=80, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_date", "id"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


class Report(BaseModel):
    """A report the assistant wrote on request, kept as Markdown.

    The Word and PDF files are rendered on download (assistant/reports.py),
    so nothing binary is stored and portal links can be made absolute for
    the host the user downloads from. The token is the only handle in the
    URL; the owner check is on `user`.
    """

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="assistant_reports")
    conversation = models.ForeignKey(Conversation, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="reports")
    message = models.ForeignKey(Message, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="reports")
    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        ordering = ["created_date", "id"]

    def __str__(self):
        return self.title

    def url(self, fmt):
        return reverse("assistant:report", kwargs={"token": self.token, "fmt": fmt})
