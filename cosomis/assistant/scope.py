"""What each signed-in user is allowed to see.

The assistant answers only from data the portal would show the same user, so
every query function in `tools.py` routes through here rather than reading
`request.user` flags itself. The rules mirror the views:

- every approved user browses the territories, the priorities registry, the
  sub-projects, the planning cycle, the photo library and the dashboards;
- partners ("investors", `not is_moderator`) see their own funding packages
  and the programmes of their organisation (`IsInvestorMixin` views filter on
  `user_id` / `organization`);
- moderators and superusers (UCP staff) see every package and every
  programme, as the moderator views do.

User accounts are never exposed: no tool reads the User table beyond the
caller's own name, role and organisation.
"""

from administrativelevels.models import Project
from investments.models import Package

ADMINISTRATOR = "administrator"
MODERATOR = "moderator"
PARTNER = "partner"


def role_of(user):
    if user.is_superuser:
        return ADMINISTRATOR
    if user.is_moderator:
        return MODERATOR
    return PARTNER


def is_staff_role(user):
    """UCP-side roles that review packages and see every programme."""
    return role_of(user) in (ADMINISTRATOR, MODERATOR)


def visible_packages(user):
    if is_staff_role(user):
        return Package.objects.all()
    return Package.objects.filter(user=user)


def visible_projects(user):
    if is_staff_role(user):
        return Project.objects.all()
    if user.organization_id is None:
        return Project.objects.none()
    return Project.objects.filter(organization=user.organization)


def describe(user):
    """Caller context handed to the model — role and organisation only."""
    return {
        "name": user.get_full_name() or user.email,
        "role": role_of(user),
        "organization": user.organization.name if user.organization else None,
    }
