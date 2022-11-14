from cosomis.celery import app
from kobotoolbox.api_call import get_all
from administrativelevels.models import AdministrativeLevel

@app.task
def kobo_request():
    all_forms = get_all()
    # print(all_forms)
    counter = 1
    results = all_forms.get('results')
    if results:
        for a in results:
            try:
                village = AdministrativeLevel.objects.filter(name=a['Village'])
                if village:
                    village_object = village.first()
                    coordinates = a['gps'].split(' ')
                    # print(counter, village_object.name, a['Village'], coordinates)
                    village_object.latitude = coordinates[0]
                    village_object.longitude = coordinates[1]
                    village_object.save()
            except Exception as exc:
                pass
            counter = counter + 1

    return all_forms
    


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls kobo_request() every 60 seconds.
    # print("Passe")
    sender.add_periodic_task(60, kobo_request.s(), name='check issues every sixty seconds')
