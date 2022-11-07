from django.shortcuts import render
from django.http import Http404

from kobotoolbox.api_call import get_all
from administrativelevels.models import AdministrativeLevel

# Create your views here.


def kobo(request):
    all_forms = get_all()
    print(all_forms)
    counter = 1
    for a in all_forms['results']:
        village = AdministrativeLevel.objects.filter(name=a['Village'])
        if village:
            village_object = village.first()
            coordinates = a['gps'].split(' ')
            print(counter, village_object.name, a['Village'], coordinates)
            village_object.latitude = coordinates[0]
            village_object.longitude = coordinates[1]
            village_object.save()
        counter = counter + 1
    raise Http404
    