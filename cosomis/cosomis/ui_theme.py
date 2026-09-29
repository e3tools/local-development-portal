"""Server-side mirror of the settings.UI_COLOR brand palettes.

The browser gets its colours from the --brand-* tokens in static/css/custom.css.
This mirror is for output that cannot read CSS variables: generated Word/PDF
reports and <meta> theme colours. Keep the values in sync with custom.css.
"""
from django.conf import settings

BRAND_PALETTES = {
    'green': {'primary': '#009639', 'primary_darker': '#00562f', 'primary_soft': '#eaf4ec'},
    'blue': {'primary': '#4f46e5', 'primary_darker': '#3730a3', 'primary_soft': '#eef2ff'},
    'red': {'primary': '#b91c1c', 'primary_darker': '#7f1d1d', 'primary_soft': '#fef2f2'},
}


def brand_palette():
    """Palette for the configured UI_COLOR (green when unset or unknown)."""
    return BRAND_PALETTES.get(getattr(settings, 'UI_COLOR', 'green'), BRAND_PALETTES['green'])
