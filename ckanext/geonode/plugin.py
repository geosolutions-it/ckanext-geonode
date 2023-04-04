import ckan.plugins as plugins
import ckan.plugins.toolkit as plugins_toolkit
from ckan.lib.plugins import DefaultTranslation

class GeoNodePlugin(plugins.SingletonPlugin, DefaultTranslation):
    """
    At the moment this plugin is only used to translate the labels in the imported resources
    """
    # ITranslation
    plugins.implements(plugins.ITranslation)