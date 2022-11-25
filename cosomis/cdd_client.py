# This library is meant to be a wrapper to connect
# To the cdd app couch db database. This depends on the
# no_sql_client.py library
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel


def iterate_administrative_level(adm_list, type):

    for administrative_level in adm_list.filter(type=type):
        print(administrative_level.name)


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

    def sync_administrative_levels(self) -> bool:

        administrative_levels = AdministrativeLevel.objects.all()
        # Sync Region
        iterate_administrative_level(administrative_levels, "Region")
        # Sync Prefecture
        iterate_administrative_level(administrative_levels, "Prefecture")
        # Sync Commune
        iterate_administrative_level(administrative_levels, "Commune")
        # Sync Canton
        iterate_administrative_level(administrative_levels, "Canton")
        # Sync Village
        iterate_administrative_level(administrative_levels, "Village")

        return True
