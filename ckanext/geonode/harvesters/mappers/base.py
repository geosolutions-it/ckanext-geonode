import json
import logging
from string import Template


from ckan.logic import NotFound, get_action
from ckan import model, plugins as p
from ckan.model import Session

from ckanext.harvest.harvesters import HarvesterBase
from ckanext.harvest.model import HarvestObject

from ckanext.geonode.harvesters import (
    CONFIG_GROUP_MAPPING,
    CONFIG_GROUP_MAPPING_FIELDNAME,
    CONFIG_IMPORT_FIELDS,

    GEONODE_JSON_TYPE,
    GeoNodeType,
)
from ckanext.geonode.harvesters.mappers.dcatapit import parse_dcatapit_info
from ckanext.geonode.harvesters.mappers.dynamic import parse_georesource
from ckanext.geonode.harvesters.utils import format_date
from ckanext.geonode.model.types import Layer, Map, Doc, GeoNodeResource


log = logging.getLogger(__name__)


def parse(harvest_object, config):
    json_dict = json.loads(harvest_object.content)
    res_type = json_dict[GEONODE_JSON_TYPE]
    parsed_type = GeoNodeType.parse_by_json_resource_type(res_type)

    if parsed_type == GeoNodeType.LAYER_TYPE:
        return parse_layer(harvest_object, harvest_object.content, config)
    elif parsed_type == GeoNodeType.MAP_TYPE:
        return parse_map(harvest_object, harvest_object.content, config)
    elif parsed_type == GeoNodeType.DOC_TYPE:
        return parse_doc(harvest_object, harvest_object.content, config)
    else:
        log.error('Unknown GeoNode type %s' % res_type)
        return None, None


def parse_layer(harvest_object, json_layer, config):
    # log.debug(f'get_layer_package_dict --> {json_layer}')
    layer = Layer(json_layer)

    package_dict, extras = parse_common(harvest_object, layer, config)
    package_dict['tags'].append({'name': 'Layer'})

    # full_layer_name = "%s:%s" % (layer.workspace(), layer.name())
    #
    # # Add WMS resource
    # resource = {}
    # resource['format'] = 'wms'
    # resource['url'] = self.source_config['geoserver_url'] + "/wms"
    # resource['name'] = full_layer_name
    # resource['description'] = p.toolkit._('WMS resource')
    # resource['geoserver_base_url'] = self.source_config['geoserver_url']
    # resource['store'] = layer.store()
    # resource['workspace'] = layer.workspace()
    # resource['layer'] = layer.name()
    # resource['is_vector'] = layer.is_vector()
    #
    # package_dict['resources'].append(resource)

    # # if it's vectorial, add a WFS resource as well. This may be used for chart preview
    # if layer.is_vector() and self._get_config_value('import_wfs_as_wfs', False):
    #     wfs_resource = {}
    #     wfs_resource['format'] = 'wfs'
    #     wfs_resource['url'] = self.source_config['geoserver_url'] + "/wfs"
    #     wfs_resource['name'] = full_layer_name
    #     wfs_resource['description'] = p.toolkit._('WFS resource')
    #     wfs_resource['geoserver_base_url'] = self.source_config['geoserver_url']
    #     wfs_resource['store'] = layer.store()
    #     wfs_resource['workspace'] = layer.workspace()
    #     wfs_resource['layer'] = layer.name()
    #     wfs_resource['is_vector'] = layer.is_vector()
    #     package_dict['resources'].append(wfs_resource)

    # # if it's vectorial, add a CSV resource as well. This may be used for chart preview
    # if layer.is_vector() and self._get_config_value('import_wfs_as_csv', False):
    #     wfs_resource = {}
    #     wfs_resource['format'] = 'csv'
    #     wfs_resource['url'] = utils.get_wfs_getfeatures_url(self.source_config['geoserver_url'], full_layer_name)
    #
    #     wfs_resource['name'] = full_layer_name
    #     wfs_resource['description'] = p.toolkit._('CSV resource')
    #     wfs_resource['geoserver_base_url'] = self.source_config['geoserver_url']
    #     wfs_resource['store'] = layer.store()
    #     wfs_resource['workspace'] = layer.workspace()
    #     wfs_resource['layer'] = layer.name()
    #     wfs_resource['is_vector'] = layer.is_vector()
    #     wfs_resource[RESOURCE_DOWNLOADER] = \
    #         WFSCSVDownloader(self.source_config['geoserver_url'], full_layer_name, layer.name() + ".csv")
    #
    #     package_dict['resources'].append(wfs_resource)

    extras['is_vector'] = layer.is_vector()

    return package_dict, extras


def parse_map(harvest_object, json_map, config):
    geomap = Map(json_map)

    package_dict, extras = parse_common(harvest_object, geomap, config)
    package_dict['tags'].append({'name': 'Map'})

    # Add main view
    package_dict['resources'].append(
        {
            'name': 'Map view',
            'description': p.toolkit._('Map client in GeoNode'),
            'format': 'html',
            'url': f'{harvest_object.source.url}/maps/{geomap.id()}/view',
        })
    # Add map details
    package_dict['resources'].append(
        {
            'name': 'Map details',
            'description': p.toolkit._('Map details in GeoNode'),
            'format': 'html',
            'url': f'{harvest_object.source.url}/maps/{geomap.id()}',
        })
    # Add WMC resource
    package_dict['resources'].append(
        {
            'name': 'Map',
            'description': p.toolkit._('Full Web Map Context'),
            'format': 'wmc',
            'url': f'{harvest_object.source.url}/maps/{geomap.id()}/wmc',
            # 'map_data': geomap.map_data()
        })

    return package_dict, extras


def parse_doc(harvest_object, json_map, config):
    doc = Doc(json_map)

    package_dict, extras = parse_common(harvest_object, doc, config)

    package_dict['tags'].append({'name': 'Doc'})

    # # Add resource
    # resource = {}
    # resource['format'] = doc.extension()
    # # Not sure about this: we're creating a resource in CKAN, so we'll have to create a URL for this.
    # # "url" is mandatory, and not providing it will raise a Validation Error
    # resource['url'] = '%s/documents/%s/download' % (harvest_object.source.url, doc.id())
    # resource['source_url'] = '%s/documents/%s/download' % (harvest_object.source.url, doc.id())
    #
    # resource['name'] = doc.doc_file()
    # resource['description'] = doc.doc_type()
    #
    # # Prepare the data downloader
    # resource[RESOURCE_DOWNLOADER] = \
    #     GeonodeDataDownloader(harvest_object.source.url, doc.id(), doc.doc_file())
    #
    # package_dict['resources'].append(resource)

    return package_dict, extras


def parse_common(harvest_object, georesource: GeoNodeResource, config: dict) -> dict:
    '''
    Create a package dict for a generic GeoNode resource
    :param harvest_object: HarvestObject domain object (with access to job and source objects)
    :type harvest_object: HarvestObject

    :param georesource: a resource (Layer or Map) from GeoNode
    :type georesource: a GeoResource (Map or Layer)

    :returns: A dataset dictionary (package_dict)
    :rtype: dict
    '''

    tags = []
    for tag in georesource.keywords():
        tag = tag['name']
        tag = tag[:50] if len(tag) > 50 else tag
        tags.append({'name': tag})

    # Infer groups
    groups = handle_groups(harvest_object, georesource, config)

    resources = []
    pos = 0

    for link in georesource.links():
        pos = pos + 1
        is_main = link.name() == georesource.alternate()
        resource = {
            'url': link.url(),
            'name': link.name(),
            'description': f'{link.name()}\n\n{link.extension()} {link.link_type()}',
            'mimetype': link.mime(),
            'format': link.extension(),
            'position': pos if not is_main else 0
        }
        if is_main:
            log.debug(f'Found main resource {link.name()}')
            resources.insert(0, resource)
        else:
            resources.append(resource)

    package_dict = {
        'title': georesource.title(),
        'notes': georesource.abstract(),
        'tags': tags,
        'resources': resources,
        'groups': groups,
    }

    # We need to get the owner organization (if any) from the harvest
    # source dataset
    source_dataset = model.Package.get(harvest_object.source.id)
    if source_dataset.owner_org:
        package_dict['owner_org'] = source_dataset.owner_org

    # Package name
    package = harvest_object.package
    if package is None or package.title != georesource.title():
        name = HarvesterBase._gen_new_name(georesource.title())
        if not name:
            name = HarvesterBase._gen_new_name(georesource.name())
        if not name:
            raise Exception(
                'Could not generate a unique name from the title or the resource name. '
                'Please choose a more unique title.')
        package_dict['name'] = name
    else:
        package_dict['name'] = package.name

    # Frequency TODO
    package_dict['frequency'] = "UNKNOWN"

    extras = {
        'guid': harvest_object.guid,
        'geonode_uuid': georesource.get('uuid'),
        'geonode_author': georesource.owner(),
        'geonode_purpose': georesource.purpose(),
        'geonode_suppinfo': georesource.get('supplemental_information'),
        'geonode_temporal_start': georesource.get('temporal_extent_start'),
        'geonode_temporal_end': georesource.get('temporal_extent_end'),
        'geonode_doi': georesource.get('doi'),
    }

    for requested_field in config.get(CONFIG_IMPORT_FIELDS, []):
        extras[requested_field] = georesource.get(requested_field)

    if georesource.date_type() == 'publication':
        extras['publication_date'] = format_date(georesource.date())

    if georesource.is_spatial():

        if georesource.srid():
            extras['spatial-reference-system'] = georesource.srid()

        ## Some of the extras we may want to add in the future:
        ## Essentials
        # 'spatial-reference-system',
        # 'guid',
        ## Usefuls
        # 'dataset-reference-date',
        # 'metadata-language',  # Language
        # 'metadata-date',  # Released
        # 'coupled-resource',
        # 'contact-email',
        # 'frequency-of-update',
        # 'spatial-data-service-type',
        # extras['progress'] = ''
        # extras['resource-type'] = ''
        # extras['licence']
        # extras['access_constraints']
        # extras['graphic-preview-file']
        # extras['graphic-preview-description']
        # extras['graphic-preview-type']
        # extras['responsible-party'] = [{'name': k, 'roles': v} for k, v in parties.items()]

        if georesource.thumbnail():
            extras['graphic-preview-file'] = georesource.thumbnail()

        x0 = x1 = y0 = y1 = None

        bbox_poly = georesource.get('ll_bbox_polygon')
        if bbox_poly:
            bbox_list = bbox_poly['coordinates']
            for bbox in bbox_list:
                for point in bbox:
                    x0 = point[0] if x0 is None or x0 > point[0] else x0
                    x1 = point[0] if x1 is None or x1 < point[0] else x1
                    y0 = point[1] if y0 is None or y0 > point[1] else y0
                    y1 = point[1] if y1 is None or y1 < point[1] else y1

            extras['bbox-east-long'] = x1
            extras['bbox-north-lat'] = y1
            extras['bbox-south-lat'] = y0
            extras['bbox-west-long'] = x0

            # Construct a GeoJSON extent so ckanext-spatial can register the extent geometry

            # Some publishers define the same two corners for the bbox (ie a point),
            # that causes problems in the search if stored as polygon
            if x0 == x1 or y0 == y1:
                log.warning(f'Point extent defined instead of polygon`')
                extent_string = Template('{"type": "Point", "coordinates": [$x, $y]}').\
                    substitute(x=x0, y=y0)
            else:
                extent_string = Template('{"type": "Polygon", '
                                         '"coordinates": [['
                                         '[$xmin, $ymin], [$xmax, $ymin], '
                                         '[$xmax, $ymax], [$xmin, $ymax], '
                                         '[$xmin, $ymin]]]}').\
                    substitute(xmin=x0, ymin=y0, xmax=x1, ymax=y1)

            extras['spatial'] = extent_string.strip()

    package_dict, extras = parse_dcatapit_info(georesource, package_dict, extras)
    package_dict, extras = parse_georesource(config, georesource, package_dict, extras)

    return package_dict, extras


def handle_groups(harvest_object, georesource, config):
    validated_groups = []

    if CONFIG_GROUP_MAPPING in config:
        source_name = config[CONFIG_GROUP_MAPPING_FIELDNAME]
        remote_value = georesource.get(source_name)
        log.debug('Field "%s" contains value "%s"', source_name, remote_value)
        if remote_value:
            # remote resource has the mapping attribute
            local_group = config[CONFIG_GROUP_MAPPING].get(str(remote_value))
            log.debug('Remote value %s maps to group %s', remote_value, local_group)

            if local_group:
                # remote attribute is mapped to a group
                log.info('Adding group %s ', local_group)

                try:
                    context = {'model': model, 'session': Session, 'user': 'harvest'}
                    data_dict = {'id': local_group}
                    get_action('group_show')(context, data_dict)
                    validated_groups.append({'name': local_group})
                except NotFound:
                    log.warning('Group %s is not available', local_group)

    return validated_groups
