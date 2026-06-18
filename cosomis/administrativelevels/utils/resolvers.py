from administrativelevels.models import AdministrativeLevel, AdministrativeLevelAlias


def resolve_adm_level(name, adm_type, parent=None):
    """
    Resolve an AdministrativeLevel by name, falling back to aliases if no
    exact match is found.

    Resolution order:
      1. Exact name match filtered by type (and parent if provided).
      2. Alias lookup filtered by type (and parent if provided).
      3. If a parent was provided and both above failed, retry 1 and 2
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
    qs = AdministrativeLevel.objects.filter(type__iexact=adm_type)
    if parent:
        qs = qs.filter(parent=parent)

    # 1. Exact name match
    result = qs.filter(name__iexact=name).first()
    if result:
        return result

    # 2. Alias lookup
    alias_qs = AdministrativeLevelAlias.objects.filter(
        name__iexact=name,
        administrative_level__type__iexact=adm_type,
    )
    if parent:
        alias_qs = alias_qs.filter(administrative_level__parent=parent)

    alias = alias_qs.select_related("administrative_level").first()
    if alias:
        return alias.administrative_level

    # 3. Fallback without parent constraint — the import file may reference a
    #    wrong parent while the node itself exists elsewhere in the hierarchy.
    if parent is not None:
        result = AdministrativeLevel.objects.filter(
            type__iexact=adm_type,
            name__iexact=name,
        ).first()
        if result:
            return result

        alias = AdministrativeLevelAlias.objects.filter(
            name__iexact=name,
            administrative_level__type__iexact=adm_type,
        ).select_related("administrative_level").first()
        if alias:
            return alias.administrative_level

    return None
