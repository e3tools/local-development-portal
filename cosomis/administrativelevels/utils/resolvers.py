import unicodedata

from administrativelevels.models import AdministrativeLevel, AdministrativeLevelAlias


def _strip_accents(s):
    """Remove accents for accent-insensitive matching."""
    return unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()


def resolve_adm_level(name, adm_type, parent=None):
    """
    Resolve an AdministrativeLevel by name, falling back to aliases if no
    exact match is found.

    Resolution order:
      1. Exact name match (iexact) filtered by type (and parent if provided).
      2. Accent-insensitive match — only for département and commune where
         the number of records is small and collision risk is low. Aliases
         handle all accent variants for arrondissement and village.
      3. Alias lookup filtered by type (and parent if provided).
      4. If a parent was provided and steps 1-3 failed, retry all three
         without the parent filter — handles cases where the import file
         places a node under a wrong parent (e.g. a village listed under
         commune NIKKI that actually lives under N'DALI in the DB).

    :param name:     The name to look up (from an import file).
    :param adm_type: The AdministrativeLevel type string as stored in the DB
                     ('village', 'arrondissement', 'commune', 'département').
    :param parent:   Optional parent AdministrativeLevel instance used to
                     disambiguate nodes that share the same name (e.g. two
                     arrondissements named 'OUENOU' under different communes).
    :return:         The matching AdministrativeLevel instance, or None.
    """
    use_accent_fallback = adm_type.lower() in ("commune", "département")
    name_stripped = _strip_accents(name) if use_accent_fallback else None

    qs = AdministrativeLevel.objects.filter(type__iexact=adm_type)
    if parent:
        qs = qs.filter(parent=parent)

    # 1. Exact name match (iexact)
    result = qs.filter(name__iexact=name).first()
    if result:
        return result

    # 2. Accent-insensitive match (commune and département only)
    if use_accent_fallback:
        for adm in qs:
            if _strip_accents(adm.name) == name_stripped:
                return adm

    # 3. Alias lookup
    alias_qs = AdministrativeLevelAlias.objects.filter(
        name__iexact=name,
        administrative_level__type__iexact=adm_type,
    )
    if parent:
        alias_qs = alias_qs.filter(administrative_level__parent=parent)

    alias = alias_qs.select_related("administrative_level").first()
    if alias:
        return alias.administrative_level

    # 4. Fallback without parent constraint — the import file may reference a
    #    wrong parent while the node itself exists elsewhere in the hierarchy.
    if parent is not None:
        qs_no_parent = AdministrativeLevel.objects.filter(type__iexact=adm_type)

        # 4a. Exact match without parent
        result = qs_no_parent.filter(name__iexact=name).first()
        if result:
            return result

        # 4b. Accent-insensitive without parent (commune and département only)
        if use_accent_fallback:
            for adm in qs_no_parent:
                if _strip_accents(adm.name) == name_stripped:
                    return adm

        # 4c. Alias without parent
        alias = AdministrativeLevelAlias.objects.filter(
            name__iexact=name,
            administrative_level__type__iexact=adm_type,
        ).select_related("administrative_level").first()
        if alias:
            return alias.administrative_level

    return None