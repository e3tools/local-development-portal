from mixpanel import Mixpanel
from django.conf import settings
import uuid

from cosomis.utils_functions import class_name_to_sentence

mp = Mixpanel(settings.MIXPANEL_TOKEN)

def track_event(request, user_id, event_name, properties=None):
    properties = properties or {}
    
    properties.update({
        "$ip": request.META.get("REMOTE_ADDR"),
        "$user_agent": request.META.get("HTTP_USER_AGENT"),
    })

    mp.track(user_id, event_name, properties)

def set_user_profile(user_id, properties):
    mp.people_set(user_id, properties)


def get_anonymous_id(request):
    if not request.session.get("anon_id"):
        request.session["anon_id"] = str(uuid.uuid4())
    return request.session["anon_id"]

def track_user_activity(request, class_name):
    try:
        if class_name == 'IndexListView':
            class_name = 'InvestmentsPageView'

        sentence_class_name = class_name_to_sentence(class_name)
        
        if request.user.is_authenticated:
            user = request.user

            anon_id = request.session.get("anon_id")
            if anon_id:
                mp.alias(str(user.id), anon_id)
                del request.session["anon_id"]

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