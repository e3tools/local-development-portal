"""The assistant's model loop: OpenAI Chat Completions with function calling.

`run_turn` sends the conversation plus the tool schemas, executes whatever
tools the model asks for (through `tools.call_tool`, which applies the
caller's scope), feeds the results back, and repeats until the model answers
in text or the round limit is hit. Nothing here writes to the database.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from django.conf import settings

from assistant import scope, tools

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the assistant of the Local Development Portal (LDP), the community-driven
development information system of the COSO programme in Togo. You help signed-in
users understand the portal's data: territories (regions, prefectures, communes,
cantons, villages), village profiles, the local priorities registry, funded
sub-projects, the CDD planning cycle, funding programmes and investment packages.

Rules:
- Answer only from what the tools return. Never invent, estimate or extrapolate a
  figure. If the tools cannot answer, say so plainly and suggest what the user
  could look at instead.
- You are strictly read-only. You cannot create, fund, approve or change anything;
  if asked to, explain that and point to the page where the user can do it.
- The tools already apply the user's access rights. If a tool returns nothing or
  a limited scope, that is what this user is allowed to see — do not speculate
  about data outside it, and never discuss other users or their accounts.
- Reply in the language of the user's question (French or English). Use the
  portal's own terms (priorité, sous-projet, canton, CVD, CCD…).
- Be concise. Lead with the answer, then the key figures, in a short table when
  there are several rows. Amounts are in FCFA; format them with thin separators
  (e.g. 12 500 000 FCFA).
- Every entity you mention should link to its portal page using the `url` the
  tools return, as Markdown links with relative paths.
- Row counts are capped; when a result says `count` is larger than `returned`,
  say the list is truncated and suggest a narrower filter.
- End with one line: "Calculé à partir des données du portail — ceci n'est pas
  une déclaration officielle de l'UCP." (or its English equivalent).
"""

MAX_TOOL_ROUNDS = 6
MAX_HISTORY = 12


@dataclass
class Reply:
    answer: str
    tool_trace: list = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""


class AssistantUnavailable(Exception):
    """No API key configured, or the provider could not be reached."""


def is_configured():
    return bool(settings.OPENAI_API_KEY)


def build_client():
    if not is_configured():
        raise AssistantUnavailable("OPENAI_API_KEY is not configured.")
    from openai import OpenAI

    kwargs = {"api_key": settings.OPENAI_API_KEY, "timeout": 45.0, "max_retries": 1}
    if settings.OPENAI_BASE_URL:
        kwargs["base_url"] = settings.OPENAI_BASE_URL
    return OpenAI(**kwargs)


def _caller_block(user):
    who = scope.describe(user)
    org = f", organisation: {who['organization']}" if who["organization"] else ""
    return (f"Signed-in user: {who['name']} (role: {who['role']}{org}). "
            "Partners see their own packages and their organisation's programmes; "
            "moderators and administrators see all of them.")


def _assistant_message(msg):
    """Re-serialise the model's tool-calling turn so it can be replayed."""
    out = {"role": "assistant", "content": msg.content or ""}
    if msg.tool_calls:
        out["tool_calls"] = [{
            "id": tc.id, "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
        } for tc in msg.tool_calls]
    return out


def run_turn(user, history, question, client=None):
    """Answer `question` for `user`, given prior (role, content) text turns."""
    client = client or build_client()
    model = settings.ASSISTANT_MODEL
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": _caller_block(user)},
    ]
    for role, content in history[-MAX_HISTORY:]:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question})

    reply = Reply(answer="", model=model)
    from openai import APIConnectionError, APIStatusError, AuthenticationError

    for _round in range(MAX_TOOL_ROUNDS + 1):
        try:
            response = client.chat.completions.create(
                model=model, messages=messages, tools=tools.TOOL_SCHEMAS,
                tool_choice="auto" if _round < MAX_TOOL_ROUNDS else "none",
            )
        except AuthenticationError as exc:
            raise AssistantUnavailable("The assistant's API key was rejected.") from exc
        except APIStatusError as exc:
            raise AssistantUnavailable(
                f"The assistant's provider returned an error ({exc.status_code}).") from exc
        except APIConnectionError as exc:
            raise AssistantUnavailable("The assistant's provider could not be reached.") from exc

        if response.usage:
            reply.prompt_tokens += response.usage.prompt_tokens or 0
            reply.completion_tokens += response.usage.completion_tokens or 0

        msg = response.choices[0].message
        if not msg.tool_calls:
            reply.answer = (msg.content or "").strip()
            return reply

        messages.append(_assistant_message(msg))
        for call in msg.tool_calls:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments, result = {}, {"error": "Arguments were not valid JSON."}
            else:
                try:
                    result = tools.call_tool(user, call.function.name, arguments)
                except Exception:  # noqa: BLE001 — a tool bug must not kill the turn
                    log.exception("assistant tool %s failed", call.function.name)
                    result = {"error": f"{call.function.name} failed unexpectedly."}
            reply.tool_trace.append({"tool": call.function.name, "arguments": arguments,
                                     "rows": _size(result)})
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})

    reply.answer = ("I could not finish computing an answer within the allowed "
                    "number of steps. Please narrow the question.")
    return reply


def _size(result):
    if isinstance(result, dict):
        for key in ("returned", "count", "villages", "total"):
            if isinstance(result.get(key), int):
                return result[key]
    return None
