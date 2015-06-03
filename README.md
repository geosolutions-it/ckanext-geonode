ckanext-geonode
==================

GeoNode harvester for CKAN
--------------------------

Harvests GeoNode instances using GeoNode's own API.

Even if GeoNode may be queried using CSW, there are some issues in parsing the ISO19139 document, such as identifiyng the resource type (some versions do not differentiate between
maps and layers). Furthermore, by using the internal API, we can retrieve some more information, such as the gxp map configuration json.

