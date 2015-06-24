try:
    import pkg_resources
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)

from ckanext.geonode.harvesters.geonode import GeoNodeHarvester
from ckanext.geonode.harvesters.client import GeoNodeClient
