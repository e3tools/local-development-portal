import logging
import queue
import threading
import uuid

from django.conf import settings
from mixpanel import Consumer, Mixpanel

from cosomis.utils_functions import class_name_to_sentence

logger = logging.getLogger(__name__)

# Calls to api.mixpanel.com take ~0.6s from the prod VM. They are sent from a
# background thread so pages never wait on them: short timeout, no retries
# (the library default is no timeout + 4 retries), and a bounded queue so a
# Mixpanel outage drops events instead of piling them up in memory.
REQUEST_TIMEOUT_SECONDS = 2
MAX_PENDING_CALLS = 500

# Placeholder values (env.example) that mean "Mixpanel not configured".
_PLACEHOLDER_TOKENS = ("", "test")

mp = Mixpanel(
    settings.MIXPANEL_TOKEN,
    consumer=Consumer(request_timeout=REQUEST_TIMEOUT_SECONDS, retry_limit=0),
)

_pending = queue.Queue(maxsize=MAX_PENDING_CALLS)
_worker = None
_worker_lock = threading.Lock()

# Session key holding the id of the user whose profile was already sent.
PROFILE_SENT_SESSION_KEY = "mp_profile_sent_for"


def is_enabled():
    return (settings.MIXPANEL_TOKEN or "").strip() not in _PLACEHOLDER_TOKENS


def _run_worker():
    while True:
        func, args = _pending.get()
        try:
            func(*args)
        except Exception as e:
            logger.warning("Mixpanel call %s failed: %s", func.__name__, e)
        finally:
            _pending.task_done()


def _ensure_worker():
    # Started lazily, so each gunicorn worker process gets its own thread.
    global _worker
    with _worker_lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run_worker, name="mixpanel", daemon=True)
            _worker.start()


def _enqueue(func, *args):
    """Run a Mixpanel call in the background; never blocks the request."""
    if not is_enabled():
        return
    try:
        _pending.put_nowait((func, args))
    except queue.Full:
        logger.warning("Mixpanel queue full, dropping %s", func.__name__)
        return
    _ensure_worker()


def track_event(request, user_id, event_name, properties=None):
    properties = properties or {}

    properties.update({
        "$ip": request.META.get("REMOTE_ADDR"),
        "$user_agent": request.META.get("HTTP_USER_AGENT"),
    })

    _enqueue(mp.track, user_id, event_name, properties)

def set_user_profile(user_id, properties):
    _enqueue(mp.people_set, user_id, properties)


def get_anonymous_id(request):
    if not request.session.get("anon_id"):
        request.session["anon_id"] = str(uuid.uuid4())
    return request.session["anon_id"]

def track_user_activity(request, class_name):
    if not is_enabled():
        return
    try:
        if class_name == 'IndexListView':
            class_name = 'InvestmentsPageView'

        sentence_class_name = class_name_to_sentence(class_name)

        if request.user.is_authenticated:
            user = request.user

            anon_id = request.session.get("anon_id")
            if anon_id:
                _enqueue(mp.alias, str(user.id), anon_id)
                del request.session["anon_id"]

            # The profile rarely changes: send it once per session, not on
            # every page view.
            if request.session.get(PROFILE_SENT_SESSION_KEY) != user.id:
                properties = {
                    "$email": user.email,
                    "$name": user.get_full_name(),
                    "$created": user.date_joined.isoformat(),
                    "$organization": user.organization.name if user.organization else None,
                    "$is_moderator": "Yes" if user.is_moderator else 'No'
                }

                if user.photo:
                    if 'http:' in user.photo.url:
                        url = user.photo.url.split('?')[0]
                    else:
                        url = request.build_absolute_uri(user.photo.url)
                    properties.update({
                        "$avatar": url
                    })

                set_user_profile(
                    str(user.id),
                    properties
                )
                request.session[PROFILE_SENT_SESSION_KEY] = user.id

            track_event(
                request,
                str(user.id),
                sentence_class_name,
            )
        else:
            track_event(
                request,
                get_anonymous_id(request),
                "Page Viewed"
            )
    except Exception as e:
        print(f"Error tracking event: {e}")
