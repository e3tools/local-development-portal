# This library is meant to be a wrapper to connect
# To the cdd app couch db database. This depends on the
# no_sql_client.py library
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel


class CddClient:

    def __init__(self):
        self.nsc = NoSQLClient()
        self.adm_db = self.nsc.get_db("administrative_levels")

    def create_administrative_level(self, adm_obj):
        # TODO: You need to manage the parent id from couch.
        # TODO 2: You need to manage the administrative_id.
        data = {
            "name": adm_obj.name,
            "administrative_level": adm_obj.type,
            "type": "administrative_level",
            "parent_id": "",
            "latitude": adm_obj.latitude,
            "longitude": adm_obj.longitude,
        }
        self.nsc.create_document(self.adm_db, data)
        return True

    def sync_administrative_levels(self):

        administrative_levels = AdministrativeLevel.objects.all()

        for administrative_level in administrative_levels.filter(type='Region'):
            print(administrative_level.name)

        for administrative_level in administrative_levels.filter(type='Prefecture'):
            print(administrative_level.name)

        for administrative_level in administrative_levels.filter(type='Commune'):
            print(administrative_level.name)

        for administrative_level in administrative_levels.filter(type='Canton'):
            print(administrative_level.name)

        for administrative_level in administrative_levels.filter(type='Village'):
            print(administrative_level.name)

        return True
