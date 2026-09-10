"""Typed, read-only query functions the assistant can call.

Each tool is a plain function taking the calling `user` plus keyword
arguments that match its JSON schema, and returning JSON-serialisable data.
They only ever read through the ORM, cap their row counts, apply the caller's
scope (see `scope.py`) and attach a portal URL to every entity they return so
answers can link back to the page the figure came from.

The model never sees a queryset, a SQL string or a Python object — only what
these functions return.
"""

from __future__ import annotations

from django.db.models import Count, Q, Sum
from django.urls import reverse

from administrativelevels.models import AdministrativeLevel, Sector, Task
from investments.models import Attachment, Investment, Package
from assistant import scope

MAX_ROWS = 50
DEFAULT_ROWS = 25

# Plain English labels rather than the models' lazy-translated choices: they
# are used as JSON keys (a translation proxy is not a valid key) and they must
# match the values the tool schemas tell the model to pass as filters.
STATUS_LABELS = {
    Investment.NOT_FUNDED: "Not Funded", Investment.FUNDED: "Funded",
    Investment.IN_PROGRESS: "In Progress", Investment.COMPLETED: "Completed",
    Investment.PAUSED: "Paused",
}
PACKAGE_STATUS_LABELS = {
    Package.PENDING_SUBMISSION: "Pending Submission", Package.PENDING_APPROVAL: "Pending Approval",
    Package.APPROVED: "Approved", Package.REJECTED: "Rejected",
    Package.UNDER_EXECUTION: "Under Execution", Package.PARTIALLY_APPROVED: "Partially Approved",
    Package.SELECTED_BY_GOVERNMENT: "Selected by Government",
}
LEVELS = {
    "region": AdministrativeLevel.REGION,
    "prefecture": AdministrativeLevel.PREFECTURE,
    "commune": AdministrativeLevel.COMMUNE,
    "canton": AdministrativeLevel.CANTON,
    "village": AdministrativeLevel.VILLAGE,
}
URL_NAMES = {
    AdministrativeLevel.REGION: "administrativelevels:region_detail",
    AdministrativeLevel.PREFECTURE: "administrativelevels:prefecture_detail",
    AdministrativeLevel.COMMUNE: "administrativelevels:commune_detail",
    AdministrativeLevel.CANTON: "administrativelevels:canton_detail",
    AdministrativeLevel.VILLAGE: "administrativelevels:village_detail",
}


class ToolError(Exception):
    """Raised for bad arguments; reported back to the model, never to the user."""


# -- helpers ----------------------------------------------------------------

def _limit(value):
    try:
        value = int(value or DEFAULT_ROWS)
    except (TypeError, ValueError):
        value = DEFAULT_ROWS
    return max(1, min(value, MAX_ROWS))


def _canonical_type(level):
    for alias, canonical in LEVELS.items():
        if AdministrativeLevel.matches_type(level, canonical) or level == alias:
            return canonical
    return None


def _level_url(level):
    canonical = _canonical_type(level.type)
    name = URL_NAMES.get(canonical, "administrativelevels:detail")
    return reverse(name, args=[level.id])


def _ancestors(level):
    chain, node = [], level.parent
    while node is not None:
        chain.append(node)
        node = node.parent
    return chain


def _descendant_ids(level):
    """Every locality under `level`, itself included (one query per depth)."""
    ids, frontier = [level.id], [level.id]
    while frontier:
        frontier = list(AdministrativeLevel.objects.filter(
            parent_id__in=frontier).values_list("id", flat=True))
        ids.extend(frontier)
    return ids


def _resolve_locality(name_or_id, level=None):
    qs = AdministrativeLevel.objects.all()
    if level:
        canonical = _canonical_type(level)
        if canonical is None:
            raise ToolError(f"Unknown level '{level}'; use one of {list(LEVELS)}.")
        qs = qs.filter(AdministrativeLevel.type_filter_q(canonical))
    if isinstance(name_or_id, int) or str(name_or_id).isdigit():
        match = qs.filter(id=int(name_or_id)).first()
    else:
        match = (qs.filter(name__iexact=str(name_or_id)).first()
                 or qs.filter(name__icontains=str(name_or_id)).first())
    if match is None:
        raise ToolError(f"No locality matching '{name_or_id}'.")
    return match


def _brief(level):
    return {
        "id": level.id,
        "name": level.name,
        "level": level.type,
        "parent": level.parent.name if level.parent else None,
        "url": _level_url(level),
    }


def _investment_row(inv):
    village = inv.administrative_level
    return {
        "id": inv.id,
        "title": inv.title,
        "rank": inv.ranking,
        "sector": inv.sector.name,
        "village": village.name,
        "village_id": village.id,
        "canton": village.parent.name if village.parent else None,
        "estimated_cost_fcfa": inv.estimated_cost,
        "real_cost_fcfa": inv.real_cost,
        "funding_status": STATUS_LABELS.get(inv.project_status, inv.project_status),
        "funded_by": inv.funded_by.name if inv.funded_by else None,
        "physical_execution_pct": inv.physical_execution_rate,
        "financial_execution_pct": inv.financial_implementation_rate,
        "endorsed_by": [k for k, v in (
            ("women", inv.endorsed_by_women), ("youth", inv.endorsed_by_youth),
            ("farmers", inv.endorsed_by_agriculturist),
            ("pastoralists", inv.endorsed_by_pastoralist)) if v],
        "climate_contribution": inv.climate_contribution,
        "url": _level_url(village),
    }


def _scoped_investments(kind, region=None, prefecture=None, commune=None,
                        canton=None, village=None, sector=None, rank=None,
                        funding=None):
    qs = Investment.objects.filter(investment_status=kind).select_related(
        "administrative_level__parent", "sector", "funded_by")
    for name, level in ((region, "region"), (prefecture, "prefecture"),
                        (commune, "commune"), (canton, "canton"), (village, "village")):
        if name:
            qs = qs.filter(administrative_level_id__in=_descendant_ids(
                _resolve_locality(name, level)))
    if sector:
        qs = qs.filter(sector__name__icontains=sector)
    if rank:
        qs = qs.filter(ranking=int(rank))
    if funding == "unfunded":
        qs = qs.filter(project_status=Investment.NOT_FUNDED)
    elif funding == "funded":
        qs = qs.exclude(project_status=Investment.NOT_FUNDED)
    elif funding:
        code = {v.lower(): k for k, v in STATUS_LABELS.items()}.get(str(funding).lower())
        if code:
            qs = qs.filter(project_status=code)
    return qs


# -- tools -------------------------------------------------------------------

def portal_overview(user):
    """Headline counts for the whole portal."""
    levels = {
        alias: AdministrativeLevel.objects.filter(
            AdministrativeLevel.type_filter_q(canonical)).count()
        for alias, canonical in LEVELS.items()
    }
    priorities = Investment.objects.filter(investment_status=Investment.PRIORITY)
    works = Investment.objects.filter(investment_status=Investment.SUBPROJECT)
    by_region = []
    for region in AdministrativeLevel.objects.filter(
            AdministrativeLevel.type_filter_q(AdministrativeLevel.REGION)):
        ids = _descendant_ids(region)
        by_region.append({
            "region": region.name,
            "villages": AdministrativeLevel.objects.filter(
                id__in=ids, **{"type__iexact": AdministrativeLevel.VILLAGE}).count(),
            "priorities": priorities.filter(administrative_level_id__in=ids).count(),
            "unfunded_priorities": priorities.filter(
                administrative_level_id__in=ids,
                project_status=Investment.NOT_FUNDED).count(),
            "subprojects": works.filter(administrative_level_id__in=ids).count(),
            "url": _level_url(region),
        })
    return {
        "localities": levels,
        "priorities_total": priorities.count(),
        "priorities_unfunded": priorities.filter(project_status=Investment.NOT_FUNDED).count(),
        "priorities_estimated_cost_fcfa": priorities.aggregate(s=Sum("estimated_cost"))["s"] or 0,
        "subprojects_total": works.count(),
        "subprojects_by_status": {
            STATUS_LABELS.get(r["project_status"], r["project_status"]): r["n"]
            for r in works.values("project_status").annotate(n=Count("id"))
        },
        "photos": Attachment.objects.filter(type=Attachment.PHOTO).count(),
        "by_region": by_region,
    }


def find_localities(user, query=None, level=None, within=None, limit=None):
    """Search localities by (partial) name and/or level, optionally inside a parent."""
    qs = AdministrativeLevel.objects.select_related("parent")
    if level:
        canonical = _canonical_type(level)
        if canonical is None:
            raise ToolError(f"Unknown level '{level}'; use one of {list(LEVELS)}.")
        qs = qs.filter(AdministrativeLevel.type_filter_q(canonical))
    if within:
        qs = qs.filter(id__in=_descendant_ids(_resolve_locality(within)))
    if query:
        qs = qs.filter(name__icontains=query)
    rows = [_brief(l) for l in qs.order_by("type", "name")[:_limit(limit)]]
    return {"count": qs.count(), "returned": len(rows), "localities": rows}


def locality_profile(user, locality, level=None):
    """Full profile of one locality: demography, infrastructure, priorities, cycle."""
    node = _resolve_locality(locality, level)
    ids = _descendant_ids(node)
    priorities = Investment.objects.filter(
        investment_status=Investment.PRIORITY, administrative_level_id__in=ids)
    works = Investment.objects.filter(
        investment_status=Investment.SUBPROJECT, administrative_level_id__in=ids)
    profile = {
        **_brief(node),
        "hierarchy": [_brief(a) for a in _ancestors(node)],
        "children": {
            r["type"]: r["n"] for r in AdministrativeLevel.objects.filter(
                parent=node).values("type").annotate(n=Count("id"))
        },
        "villages_in_scope": AdministrativeLevel.objects.filter(
            id__in=ids, type__iexact=AdministrativeLevel.VILLAGE).count(),
        "priorities": {
            "total": priorities.count(),
            "unfunded": priorities.filter(project_status=Investment.NOT_FUNDED).count(),
            "estimated_cost_fcfa": priorities.aggregate(s=Sum("estimated_cost"))["s"] or 0,
            "by_sector": {
                r["sector__name"]: r["n"] for r in
                priorities.values("sector__name").annotate(n=Count("id")).order_by("-n")
            },
            "top_ranked": [_investment_row(i) for i in priorities.filter(
                ranking=1).select_related(
                "administrative_level__parent", "sector", "funded_by")[:10]],
        },
        "subprojects": {
            "total": works.count(),
            "by_status": {
                STATUS_LABELS.get(r["project_status"], r["project_status"]): r["n"]
                for r in works.values("project_status").annotate(n=Count("id"))
            },
        },
        "photos": Attachment.objects.filter(adm_id__in=ids, type=Attachment.PHOTO).count(),
    }
    if node.is_village():
        tasks = Task.objects.filter(activity__phase__village=node)
        total, done = tasks.count(), tasks.filter(status=Task.COMPLETED).count()
        current = node.get_current_task()
        profile.update({
            "population": {
                "total": node.total_population, "women": node.population_women,
                "men": node.population_men, "young": node.population_young,
                "elderly": node.population_elder,
                "persons_with_disabilities": node.population_handicap,
                "farmers": node.population_agriculturist,
                "pastoralists": node.population_pastoralist,
                "minorities": node.population_minorities,
            },
            "languages": node.main_languages,
            "rural": node.rural,
            "border_area": node.frontalier,
            "coordinates": ({"lat": float(node.latitude), "lng": float(node.longitude)}
                            if node.latitude is not None else None),
            "infrastructure": node.infrastructure,
            "facilitator": node.facilitator,
            "priorities_identified_on": (node.identified_priority.isoformat()
                                         if node.identified_priority else None),
            "planning_cycle": {
                "tasks_total": total,
                "tasks_completed": done,
                "completion_pct": round(done * 100 / total, 1) if total else None,
                "last_completed_task": current.name if current else None,
                "current_phase": (current.activity.phase.name if current else None),
                "phases": [
                    {"name": p.name, "order": p.order, "status": p.get_status()}
                    for p in node.phases.all().order_by("order")
                ],
            },
        })
    return profile


def list_priorities(user, region=None, prefecture=None, commune=None, canton=None,
                    village=None, sector=None, rank=None, funding=None, limit=None):
    """Priorities registered by village assemblies, filtered and ranked."""
    qs = _scoped_investments(Investment.PRIORITY, region, prefecture, commune,
                             canton, village, sector, rank, funding)
    rows = [_investment_row(i) for i in qs.order_by(
        "administrative_level__name", "ranking")[:_limit(limit)]]
    return {
        "count": qs.count(),
        "estimated_cost_fcfa": qs.aggregate(s=Sum("estimated_cost"))["s"] or 0,
        "returned": len(rows),
        "priorities": rows,
    }


def aggregate_priorities(user, group_by="sector", region=None, prefecture=None,
                         commune=None, canton=None, village=None, sector=None,
                         rank=None, funding=None):
    """Count priorities and sum their estimated cost, grouped by one dimension."""
    qs = _scoped_investments(Investment.PRIORITY, region, prefecture, commune,
                             canton, village, sector, rank, funding)
    fields = {
        "sector": "sector__name",
        "rank": "ranking",
        "funding_status": "project_status",
        "programme": "funded_by__name",
        "village": "administrative_level__name",
        "canton": "administrative_level__parent__name",
        "commune": "administrative_level__parent__parent__name",
        "prefecture": "administrative_level__parent__parent__parent__name",
        "region": "administrative_level__parent__parent__parent__parent__name",
    }
    field = fields.get(group_by)
    if field is None:
        raise ToolError(f"group_by must be one of {list(fields)}.")
    groups = []
    for r in qs.values(field).annotate(
            n=Count("id"), cost=Sum("estimated_cost")).order_by("-n")[:MAX_ROWS]:
        key = r[field]
        if group_by == "funding_status":
            key = STATUS_LABELS.get(key, key)
        groups.append({group_by: key, "priorities": r["n"],
                       "estimated_cost_fcfa": r["cost"] or 0})
    return {"group_by": group_by, "total": qs.count(), "groups": groups}


def list_subprojects(user, region=None, prefecture=None, commune=None, canton=None,
                     village=None, sector=None, funding=None, min_physical_pct=None,
                     max_physical_pct=None, limit=None):
    """Sub-projects (works) with execution rates, costs and contractor."""
    qs = _scoped_investments(Investment.SUBPROJECT, region, prefecture, commune,
                             canton, village, sector, None, funding)
    if min_physical_pct is not None:
        qs = qs.filter(physical_execution_rate__gte=int(min_physical_pct))
    if max_physical_pct is not None:
        qs = qs.filter(physical_execution_rate__lte=int(max_physical_pct))
    rows = []
    for inv in qs.order_by("-physical_execution_rate")[:_limit(limit)]:
        row = _investment_row(inv)
        row.update({
            "contractor": inv.responsible_structure,
            "start_date": inv.start_date.isoformat() if inv.start_date else None,
            "duration_days": inv.duration,
            "delays_consumed_days": inv.delays_consumed,
        })
        rows.append(row)
    agg = qs.aggregate(est=Sum("estimated_cost"), real=Sum("real_cost"))
    return {
        "count": qs.count(),
        "estimated_cost_fcfa": agg["est"] or 0,
        "real_cost_fcfa": agg["real"] or 0,
        "by_status": {
            STATUS_LABELS.get(r["project_status"], r["project_status"]): r["n"]
            for r in qs.values("project_status").annotate(n=Count("id"))
        },
        "returned": len(rows),
        "subprojects": rows,
    }


def planning_cycle_status(user, region=None, prefecture=None, commune=None,
                          canton=None):
    """How far villages have progressed through the CDD planning cycle."""
    villages = AdministrativeLevel.objects.filter(
        AdministrativeLevel.type_filter_q(AdministrativeLevel.VILLAGE))
    for name, level in ((region, "region"), (prefecture, "prefecture"),
                        (commune, "commune"), (canton, "canton")):
        if name:
            villages = villages.filter(id__in=_descendant_ids(_resolve_locality(name, level)))
    tasks = Task.objects.filter(activity__phase__village__in=villages)
    total, done = tasks.count(), tasks.filter(status=Task.COMPLETED).count()
    phase_progress = []
    for name in tasks.values_list("activity__phase__name", flat=True).distinct().order_by(
            "activity__phase__order"):
        sub = tasks.filter(activity__phase__name=name)
        phase_progress.append({
            "phase": name,
            "tasks": sub.count(),
            "completed": sub.filter(status=Task.COMPLETED).count(),
            "in_progress": sub.filter(status=Task.IN_PROGRESS).count(),
            "blocked": sub.filter(status=Task.ERROR).count(),
        })
    blocked = list(villages.filter(
        phases__activities__tasks__status=Task.ERROR).distinct()[:MAX_ROWS])
    return {
        "villages": villages.count(),
        "tasks_total": total,
        "tasks_completed": done,
        "completion_pct": round(done * 100 / total, 1) if total else None,
        "by_phase": phase_progress,
        "villages_needing_attention": [_brief(v) for v in blocked],
    }


def list_sectors(user):
    """Sectors and their category, with priority counts."""
    return {"sectors": [
        {"sector": s.name, "category": s.category.name,
         "priorities": s.investments.filter(investment_status=Investment.PRIORITY).count(),
         "subprojects": s.investments.filter(investment_status=Investment.SUBPROJECT).count()}
        for s in Sector.objects.select_related("category").order_by("category__name", "name")
    ]}


def list_programmes(user, limit=None):
    """Funding programmes visible to the caller (own organisation for partners)."""
    qs = scope.visible_projects(user).select_related("organization")
    rows = []
    for p in qs.order_by("name")[:_limit(limit)]:
        rows.append({
            "id": p.id,
            "name": p.name,
            "organization": p.organization.name if p.organization else None,
            "implementation_partner": p.implementation_partner,
            "source_of_financing": p.source_of_financing,
            "total_amount_fcfa": p.total_amount,
            "start_date": p.start_date.isoformat() if p.start_date else None,
            "end_date": p.end_date.isoformat() if p.end_date else None,
            "sectors": [c.name for c in p.sectors.all()],
            "funded_priorities": p.investments.filter(
                investment_status=Investment.PRIORITY).count(),
            "subprojects": p.investments.filter(
                investment_status=Investment.SUBPROJECT).count(),
            "url": reverse("administrativelevels:project-detail", args=[p.id]),
        })
    return {"count": qs.count(), "scope": ("all programmes" if scope.is_staff_role(user)
                                          else "your organisation's programmes"),
            "programmes": rows}


def list_packages(user, status=None, limit=None):
    """Funding packages: the caller's own for partners, all for moderators."""
    qs = scope.visible_packages(user).select_related(
        "user__organization", "project", "review_by").annotate(
        n_items=Count("funded_investments"))
    if status:
        code = {v.lower(): k for k, v in PACKAGE_STATUS_LABELS.items()}.get(
            str(status).lower(), status)
        qs = qs.filter(status=code)
    rows = []
    for pkg in qs.order_by("-updated_date")[:_limit(limit)]:
        items = pkg.funded_investments.select_related(
            "administrative_level", "sector")[:MAX_ROWS]
        rows.append({
            "id": pkg.id,
            "status": PACKAGE_STATUS_LABELS.get(pkg.status, pkg.status),
            "draft": pkg.draft_status,
            "partner_organization": (pkg.user.organization.name
                                     if pkg.user.organization else None),
            "programme": pkg.project.name if pkg.project else None,
            "source": pkg.source,
            "reviewed": pkg.review_by is not None,
            "rejection_reason": pkg.rejection_reason,
            "items": pkg.n_items,
            "estimated_cost_fcfa": pkg.estimated_final_cost() or 0,
            "updated": pkg.updated_date.date().isoformat() if pkg.updated_date else None,
            "investments": [{
                "title": i.title, "village": i.administrative_level.name,
                "sector": i.sector.name, "estimated_cost_fcfa": i.estimated_cost,
                "url": _level_url(i.administrative_level),
            } for i in items],
        })
    return {
        "count": qs.count(),
        "scope": ("all packages" if scope.is_staff_role(user) else "your own packages"),
        "by_status": {
            PACKAGE_STATUS_LABELS.get(r["status"], r["status"]): r["n"]
            for r in qs.values("status").annotate(n=Count("id"))
        },
        "packages": rows,
    }


# -- registry ----------------------------------------------------------------

_LOCALITY_FILTERS = {
    "region": {"type": "string", "description": "Region name, e.g. 'Savanes'."},
    "prefecture": {"type": "string", "description": "Prefecture name, e.g. 'Kozah'."},
    "commune": {"type": "string", "description": "Commune name, e.g. 'Tône 1'."},
    "canton": {"type": "string", "description": "Canton name, e.g. 'Nano'."},
    "village": {"type": "string", "description": "Village name or id."},
}
_INVESTMENT_FILTERS = {
    **_LOCALITY_FILTERS,
    "sector": {"type": "string", "description": "Sector name or part of it, e.g. 'Eau'."},
    "funding": {"type": "string",
                "description": "'funded', 'unfunded', or an exact status: Not Funded, "
                               "Funded, In Progress, Completed, Paused."},
}
_LIMIT = {"type": "integer", "description": f"Rows to return (default {DEFAULT_ROWS}, max {MAX_ROWS})."}


def _spec(name, fn, properties, required=()):
    return {
        "name": name,
        "function": fn,
        "schema": {
            "type": "function",
            "function": {
                "name": name,
                "description": (fn.__doc__ or "").strip(),
                "parameters": {"type": "object", "properties": properties,
                               "required": list(required)},
            },
        },
    }


TOOLS = [
    _spec("portal_overview", portal_overview, {}),
    _spec("find_localities", find_localities, {
        "query": {"type": "string", "description": "Part of a locality name."},
        "level": {"type": "string", "enum": list(LEVELS)},
        "within": {"type": "string", "description": "Name or id of a parent locality."},
        "limit": _LIMIT,
    }),
    _spec("locality_profile", locality_profile, {
        "locality": {"type": "string", "description": "Locality name or id."},
        "level": {"type": "string", "enum": list(LEVELS),
                  "description": "Disambiguates when several levels share a name."},
    }, required=["locality"]),
    _spec("list_priorities", list_priorities, {
        **_INVESTMENT_FILTERS,
        "rank": {"type": "integer", "description": "Priority rank (1 = top)."},
        "limit": _LIMIT,
    }),
    _spec("aggregate_priorities", aggregate_priorities, {
        "group_by": {"type": "string", "enum": [
            "sector", "rank", "funding_status", "programme", "village", "canton",
            "commune", "prefecture", "region"]},
        **_INVESTMENT_FILTERS,
        "rank": {"type": "integer"},
    }, required=["group_by"]),
    _spec("list_subprojects", list_subprojects, {
        **_INVESTMENT_FILTERS,
        "min_physical_pct": {"type": "integer"},
        "max_physical_pct": {"type": "integer"},
        "limit": _LIMIT,
    }),
    _spec("planning_cycle_status", planning_cycle_status, {
        k: v for k, v in _LOCALITY_FILTERS.items() if k != "village"}),
    _spec("list_sectors", list_sectors, {}),
    _spec("list_programmes", list_programmes, {"limit": _LIMIT}),
    _spec("list_packages", list_packages, {
        "status": {"type": "string", "description": "Pending Submission, Pending Approval, "
                                                    "Approved, Rejected, Partially Approved."},
        "limit": _LIMIT,
    }),
]
TOOLS_BY_NAME = {t["name"]: t for t in TOOLS}
TOOL_SCHEMAS = [t["schema"] for t in TOOLS]


def call_tool(user, name, arguments):
    """Run one tool for `user`; unknown names and bad inputs become error payloads."""
    spec = TOOLS_BY_NAME.get(name)
    if spec is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return spec["function"](user, **(arguments or {}))
    except ToolError as exc:
        return {"error": str(exc)}
    except TypeError as exc:
        return {"error": f"Bad arguments for {name}: {exc}"}
