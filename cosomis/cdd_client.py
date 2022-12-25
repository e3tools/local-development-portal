# This library is meant to be a wrapper to connect
# To the cdd app couch db database. This depends on the
# no_sql_client.py library
from no_sql_client import NoSQLClient

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
            "administrative_id": adm_obj.id,
            "parent_id": "",
            "latitude": str(adm_obj.latitude),
            "longitude": str(adm_obj.longitude),
        }
        self.nsc.create_document(self.adm_db, data)
        new = self.adm_db.get_query_result(
            {
                "type": 'administrative_level',
                "administrative_id": adm_obj.id,
            }
        )
        final = None
        for obj in new:
            final = obj
        return final['_id']

    def sync_administrative_levels(self, administrative_levels) -> bool:

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

    def update_administrative_level(self, obj) -> bool:
        administrative_level = self.adm_db[
             obj.no_sql_db_id
        ]
        print(administrative_level)
        parent = ""
        if obj.parent:
            parent = str(obj.parent.id)
        data = {
            "name": obj.name,
            "administrative_level": obj.type,
            "parent_id": parent,
            "latitude": str(obj.latitude),
            "longitude": str(obj.longitude),
        }
        for k, v in data.items():
            if v:
                administrative_level[k] = v
        administrative_level.save()
        return True


