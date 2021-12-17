# try:
#     import pkg_resources
#     pkg_resources.declare_namespace(__name__)
# except ImportError:
#     import pkgutil
#     __path__ = pkgutil.extend_path(__path__, __name__)
#
# from ckanext.geonode.harvesters.geonode import GeoNodeHarvester
# from ckanext.geonode.harvesters.client import GeoNodeClient


GEONODE_TYPE = 'GEONODE_TYPE__'
GEONODE_LAYER_TYPE = 'LAYER'
GEONODE_MAP_TYPE = 'MAP'
GEONODE_DOC_TYPE = 'DOC'

RESOURCE_DOWNLOADER = 'DOWNLOADER__'

TEMP_FILE_THRESHOLD_SIZE = 5 * 1024 * 1024

CONFIG_GEOSERVERURL = 'geoserver_url'
CONFIG_KEYWORD_MAPPING = 'keyword_group_mapping'
CONFIG_GROUP_MAPPING_FIELDNAME = 'group_mapping_fieldname'
CONFIG_GROUP_MAPPING = 'group_mapping'
CONFIG_IMPORT_FIELDS = 'import_fields'