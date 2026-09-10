"""Scoping and loop tests for the portal assistant.

The model is replaced by a scripted fake, so these run without a key and
without network. What they pin down is the part that must never regress: a
partner only ever sees their own packages and their organisation's
programmes, a moderator sees everything, no tool exposes user accounts, and
a tool call the model asks for is executed and recorded on the answer.
"""

import json
from types import SimpleNamespace
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from assistant import agent, tools
from assistant.models import Conversation, Message
from investments.models import Package
from usermanager.models import User

PASSWORD = "DemoCOSO2026!"


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id, type="function",
        function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def scripted(*turns):
    """A fake OpenAI client replaying `turns`: each is text or a list of tool calls."""

    class Completions:
        def __init__(self):
            self.requests = []

        def create(self, **kwargs):
            self.requests.append(kwargs)
            turn = turns[min(len(self.requests) - 1, len(turns) - 1)]
            if isinstance(turn, str):
                message = SimpleNamespace(content=turn, tool_calls=None)
            else:
                message = SimpleNamespace(content=None, tool_calls=turn)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=message)],
                usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))

    completions = Completions()
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


class SeededTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_togo_demo", villages=12, verbosity=0)
        cls.admin = User.objects.get(email="admin@coso-demo.tg")
        cls.moderator = User.objects.get(email="moderateur@coso-demo.tg")
        cls.partner = User.objects.get(email="banque.mondiale@coso-demo.tg")
        cls.other_partner = User.objects.get(email="pnud@coso-demo.tg")


class ScopingTests(SeededTestCase):
    def test_partner_sees_only_own_packages(self):
        result = tools.list_packages(self.partner)
        own = Package.objects.filter(user=self.partner).count()
        self.assertEqual(result["count"], own)
        self.assertGreater(own, 0)
        self.assertTrue(Package.objects.exclude(user=self.partner).exists())
        for pkg in result["packages"]:
            self.assertEqual(pkg["partner_organization"], self.partner.organization.name)

    def test_moderator_sees_all_packages(self):
        result = tools.list_packages(self.moderator)
        self.assertEqual(result["count"], Package.objects.count())
        self.assertEqual(result["scope"], "all packages")

    def test_partner_programmes_scoped_to_organisation(self):
        result = tools.list_programmes(self.partner)
        for programme in result["programmes"]:
            self.assertEqual(programme["organization"], self.partner.organization.name)
        staff = tools.list_programmes(self.admin)
        self.assertGreaterEqual(staff["count"], result["count"])

    def test_no_tool_exposes_user_accounts(self):
        payloads = [
            tools.portal_overview(self.partner),
            tools.locality_profile(self.partner, "Tamlou"),
            tools.list_priorities(self.partner, limit=5),
            tools.list_packages(self.moderator),
        ]
        dumped = json.dumps(payloads, default=str)
        self.assertNotIn("@coso-demo.tg", dumped)
        self.assertNotIn("password", dumped)

    def test_unknown_tool_and_bad_arguments_are_reported_not_raised(self):
        self.assertIn("error", tools.call_tool(self.partner, "drop_everything", {}))
        self.assertIn("error", tools.call_tool(self.partner, "locality_profile",
                                               {"locality": "Nowhere-ville"}))
        self.assertIn("error", tools.call_tool(self.partner, "aggregate_priorities",
                                               {"group_by": "colour"}))

    def test_locality_profile_links_back_to_the_portal(self):
        profile = tools.locality_profile(self.partner, "Tamlou", level="village")
        self.assertTrue(profile["url"].endswith(f"/administrative-levels/village/{profile['id']}/"))
        self.assertEqual(len(profile["planning_cycle"]["phases"]), 4)
        self.assertGreaterEqual(profile["priorities"]["total"], 4)


@override_settings(OPENAI_API_KEY="test-key", ASSISTANT_MODEL="fake-model")
class AgentLoopTests(SeededTestCase):
    def test_tool_call_is_executed_and_recorded(self):
        client = scripted([tool_call("list_packages", {"status": "Pending Approval"})],
                          "Vous avez 1 paquet en attente.")
        reply = agent.run_turn(self.partner, [], "Où en sont mes paquets ?", client=client)
        self.assertEqual(reply.answer, "Vous avez 1 paquet en attente.")
        self.assertEqual(reply.tool_trace[0]["tool"], "list_packages")
        second_request = client.chat.completions.requests[1]["messages"]
        tool_result = json.loads(second_request[-1]["content"])
        self.assertEqual(second_request[-1]["role"], "tool")
        self.assertEqual(tool_result["scope"], "your own packages")
        self.assertEqual(reply.prompt_tokens, 20)

    def test_caller_context_names_role_not_other_users(self):
        client = scripted("Bonjour.")
        agent.run_turn(self.partner, [("user", "hi"), ("assistant", "hello")], "Q", client=client)
        messages = client.chat.completions.requests[0]["messages"]
        self.assertIn("role: partner", messages[1]["content"])
        self.assertEqual([m["role"] for m in messages[2:]], ["user", "assistant", "user"])

    def test_round_limit_forces_a_text_answer(self):
        client = scripted([tool_call("portal_overview", {})])  # never stops calling tools
        reply = agent.run_turn(self.admin, [], "loop", client=client)
        self.assertEqual(len(client.chat.completions.requests), agent.MAX_TOOL_ROUNDS + 1)
        self.assertEqual(client.chat.completions.requests[-1]["tool_choice"], "none")
        self.assertIn("narrow", reply.answer)


class ViewTests(SeededTestCase):
    def test_chat_page_requires_login(self):
        self.assertEqual(self.client.get(reverse("assistant:chat")).status_code, 302)

    @override_settings(OPENAI_API_KEY="")
    def test_chat_page_explains_when_unconfigured(self):
        self.client.login(email=self.partner.email, password=PASSWORD)
        response = self.client.get(reverse("assistant:chat"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OPENAI_API_KEY")

    @override_settings(OPENAI_API_KEY="test-key")
    def test_send_persists_the_exchange_and_returns_htmx_partial(self):
        self.client.login(email=self.partner.email, password=PASSWORD)
        fake = scripted([tool_call("list_programmes", {})], "Votre organisation finance 2 programmes.")
        with mock.patch.object(agent, "build_client", return_value=fake):
            response = self.client.post(reverse("assistant:send"),
                                        {"question": "Quels programmes ?"},
                                        HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "finance 2 programmes")
        conversation = Conversation.objects.get(user=self.partner, is_active=True)
        roles = list(conversation.messages.values_list("role", flat=True))
        self.assertEqual(roles, [Message.USER, Message.ASSISTANT])
        self.assertEqual(conversation.messages.last().tool_trace[0]["tool"], "list_programmes")
        self.assertEqual(conversation.title, "Quels programmes ?")

    @override_settings(OPENAI_API_KEY="")
    def test_send_without_key_shows_error_and_keeps_only_the_question(self):
        self.client.login(email=self.moderator.email, password=PASSWORD)
        response = self.client.post(reverse("assistant:send"), {"question": "Combien ?"},
                                    HTTP_HX_REQUEST="true")
        self.assertContains(response, "OPENAI_API_KEY is not configured")  # rendered raw; the heading is translated
        self.assertEqual(Message.objects.filter(role=Message.ASSISTANT).count(), 0)

    def test_new_conversation_archives_the_active_one(self):
        self.client.login(email=self.partner.email, password=PASSWORD)
        Conversation.objects.create(user=self.partner, title="old")
        self.client.post(reverse("assistant:new"))
        self.assertFalse(Conversation.objects.filter(user=self.partner, is_active=True).exists())
