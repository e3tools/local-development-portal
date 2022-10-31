from django.shortcuts import render
from django.http import Http404

from kobotoolbox.api_call import get_all

# Create your views here.


def kobo(request):
    print(get_all())
    raise Http404
    