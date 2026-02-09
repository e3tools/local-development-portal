from django.conf import settings

def overall_variables(request):
    """Function to define globals variables"""
    return {
        'OTHER_LANGUAGES': True, #Variable to define if other languages are setuped
        'MIXPANEL_TOKEN': settings.MIXPANEL_TOKEN
    }

