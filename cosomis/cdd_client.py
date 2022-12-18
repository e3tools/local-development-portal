# This library is meant to be a wrapper to connect
# To the cdd app couch db database. This depends on the
# no_sql_client.py library
import time
from no_sql_client import NoSQLClient
from administrativelevels.models import AdministrativeLevel


class CddClient:

    def __init__(self):
        self.nsc = NoSQLClient()
        self.adm_db = self.nsc.get_db("administrative_levels")

    def iterate_administrative_level(self, adm_list, type):

        for administrative_level in adm_list.filter(type=type):
            print("CREATING", administrative_level.name)
            self.create_administrative_level(administrative_level)
            print("DONE", administrative_level.name)

    def create_administrative_level(self, adm_obj):
        # TODO: You need to manage the parent id from couch.
        # TODO 2: You need to manage the administrative_id.
        parent = None
        if adm_obj.parent:
            parent = str(adm_obj.parent.id)
        data = {
            "administrative_id": str(adm_obj.id),
            "name": adm_obj.name,
            "administrative_level": adm_obj.type,
            "type": "administrative_level",
            "parent_id": parent,
            "latitude": adm_obj.latitude,
            "longitude": adm_obj.longitude,
        }
        nosql_adm = self.nsc.create_document(self.adm_db, data)
        adm_obj.no_sql_db_id = nosql_adm['_id']
        adm_obj.save()
        return True

    def sync_administrative_levels(self) -> bool:

        administrative_levels = AdministrativeLevel.objects.all()
        # Sync Region
        self.iterate_administrative_level(administrative_levels, "Region")
        # Sync Prefecture
        self.iterate_administrative_level(administrative_levels, "Prefecture")
        # Sync Commune
        self.iterate_administrative_level(administrative_levels, "Commune")
        # Sync Canton
        self.iterate_administrative_level(administrative_levels, "Canton")
        # Sync Village
        self.iterate_administrative_level(administrative_levels, "Village")

        return True
