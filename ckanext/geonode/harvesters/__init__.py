# try:
#     import pkg_resources
#     pkg_resources.declare_namespace(__name__)
# except ImportError:
#     import pkgutil
#     __path__ = pkgutil.extend_path(__path__, __name__)
#
# from ckanext.geonode.harvesters.geonode import GeoNodeHarvester
# from ckanext.geonode.harvesters.client import GeoNodeClient

from enum import Enum

GEONODE_JSON_TYPE = 'resource_type'

RESOURCE_DOWNLOADER = 'DOWNLOADER__'

TEMP_FILE_THRESHOLD_SIZE = 5 * 1024 * 1024

CONFIG_GEOSERVERURL = 'geoserver_url'
CONFIG_KEYWORD_MAPPING = 'keyword_group_mapping'
CONFIG_GROUP_MAPPING_FIELDNAME = 'group_mapping_fieldname'
CONFIG_GROUP_MAPPING = 'group_mapping'

CONFIG_IMPORT_FIELDS = 'map_fields'
CONFIG_IMPORT_FIELDS_GND = ''
CONFIG_IMPORT_FIELDS_CKN = ''

CONFIG_IMPORT_TYPES = 'import'

CONFIG_INCLUDE_ALL_LINKS = 'include_all_links'


class GeoNodeType(Enum):

    LAYER_TYPE = 'layers', 'layers', 'layer',
    DATASET_TYPE = 'layers', 'datasets', 'dataset',
    MAP_TYPE = 'maps', 'maps', 'map',
    DOC_TYPE = 'docs', 'documents', 'document',

    def __init__(self, config_name, api_path, json_resource_type, json_resource_list=None):
        super(Enum, self).__init__()

        self.config_name = config_name
        self.api_path = api_path
        self.json_resource_type = json_resource_type
        self.json_resource_list = json_resource_list or f'{json_resource_type}s'

    @classmethod
    def get_config_names(cls):
        return [t.config_name for t in GeoNodeType]

    @classmethod
    def parse_by_json_resource_type(cls, rtype):
        for geonode_type in GeoNodeType:
            if geonode_type.json_resource_type == rtype:
                return geonode_type

    @classmethod
    def get_by_config_name(cls, cname):
        for type in GeoNodeType:
            if type.config_name == cname:
                return type


DEFAULT_HARVEST_TYPES_LIST = [
    GeoNodeType.LAYER_TYPE,
    GeoNodeType.MAP_TYPE,
    GeoNodeType.DOC_TYPE,
]