from django.conf import settings

from cosomis.ui_theme import brand_palette

def overall_variables(request):
    """Function to define globals variables"""
    return {
        'OTHER_LANGUAGES': True, #Variable to define if other languages are setuped
        'MIXPANEL_TOKEN': settings.MIXPANEL_TOKEN,
        'PROGRAM_NAME': settings.PROGRAM_NAME,
        'ENVIRONNEMENT_EXECUTION': settings.ENVIRONNEMENT_EXECUTION,
        'UI_COLOR': settings.UI_COLOR,
        'UI_PRIMARY_COLOR': brand_palette()['primary']
    }

