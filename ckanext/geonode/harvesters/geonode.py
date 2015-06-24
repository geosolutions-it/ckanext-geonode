from .client import GeoNodeClient
from .upload import MockFieldStorage

from ckanext.geonode.model.types import Layer
from ckanext.geonode.model.types import Map
from ckanext.geonode.model.types import Doc

import logging
import uuid

from string import Template
from pylons import config
from datetime import datetime

from ckan import logic
from ckan import model
from ckan import plugins as p
from ckan.model import Session

from ckan.common import json
from ckan.lib.navl.validators import not_empty

from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject
from ckanext.harvest.model import HarvestObjectExtra as HOExtra

from ckan.logic import ValidationError, NotFound, get_action


log = logging.getLogger(__name__)

GEONODE_TYPE = 'GEONODE_TYPE__'
GEONODE_LAYER_TYPE = 'LAYER'
GEONODE_MAP_TYPE = 'MAP'
GEONODE_DOC_TYPE = 'DOC'


class GeoNodeHarvester(HarvesterBase, SingletonPlugin):
    '''
    A Harvester for GeoNode's layers, map, data (todo).
    '''

    implements(IHarvester)

    _user_name = None

    source_config = {}
    geoserver_url = None

    extent_template = Template('''
    {"type": "Polygon", "coordinates": [[[$xmin, $ymin], [$xmax, $ymin], [$xmax, $ymax], [$xmin, $ymax], [$xmin, $ymin]]]}
    ''')

    def info(self):
        return {
            'name': 'geonode',
            'title': 'GeoNode harvester',
            'description': 'Harvests GeoNode instances',
            'form_config_interface': 'Text'
        }

    ## IHarvester

    def validate_config(self, source_config):
        if not source_config:
            return source_config

        try:
            source_config_obj = json.loads(source_config)

            # GeoNode does not expose the internal GeoServer URL, so we have to config it on its own
            if not 'geoserver_url' in source_config_obj:
                raise ValueError('geoserver_url is mandatory')

            if not isinstance(source_config_obj['geoserver_url'], basestring):
                raise ValueError('geoserver_url should be a string')

            if 'keyword_group_mapping' in source_config_obj:
                mapping = source_config_obj['keyword_group_mapping']
                if not isinstance(mapping, dict):
                    raise ValueError('keyword_group_mapping should be a dict (it maps group names to list of regex)')
                for k, v in mapping:
                    if not isinstance(k, basestring):
                        raise ValueError('keyword_group_mapping keys should be strings (it maps group names to list of regex)')
                    if not isinstance(v, list):
                        raise ValueError('keyword_group_mapping values should be lists (it maps group names to list of regex)')

        except ValueError as e:
            raise e

        return source_config

    def gather_stage(self, harvest_job):
        log = logging.getLogger(__name__ + '.geonode.gather')
        log.debug('GeoNode gather_stage for job: %r', harvest_job)
        # Get source URL
        url = harvest_job.source.url

        self._set_source_config(harvest_job.source.config)

        try:
            log.info('Connecting to GeoNode at %s', url)

            client = GeoNodeClient(url)

            # dict guid: layer
            harvested = {}

            for layer in client.get_layers():
                log.debug('Found layer %s %s (%s)' % (layer['id'], layer['uuid'], layer['title']))
                db_object = {
                    'id': layer['id'],
                    'uuid': layer['uuid'],
                    'title': layer['title'],
                    'type': GEONODE_LAYER_TYPE,
                    }
                harvested[layer['uuid']] = db_object

            for map in client.get_maps():
                log.debug('Found map %s %s (%s)' % (map['id'], map['uuid'], map['title']))
                db_object = {
                    'id': map['id'],
                    'uuid': map['uuid'],
                    'title': map['title'],
                    'type': GEONODE_MAP_TYPE,
                    }
                harvested[map['uuid']] = db_object

            for doc in client.get_documents():
                log.debug('Found doc %s %s (%s)' % (doc['id'], doc['uuid'], doc['title']))
                db_object = {
                    'id': doc['id'],
                    'uuid': doc['uuid'],
                    'title': doc['title'],
                    'type': GEONODE_DOC_TYPE,
                    }
                harvested[doc['uuid']] = db_object

        except Exception as e:
            self._save_gather_error('Error harvesting GeoNode: %s' % e, harvest_job)
            return None

        query = model.Session.query(HarvestObject.guid, HarvestObject.package_id).\
                                    filter(HarvestObject.current == True).\
                                    filter(HarvestObject.harvest_source_id == harvest_job.source.id)
        guid_to_package_id = {}

        for guid, package_id in query:
            guid_to_package_id[guid] = package_id

        guids_in_db = set(guid_to_package_id.keys())

        #log.debug('Starting gathering for %s' % url)
        guids_in_harvest = set(harvested.keys())

        #for doc in chobj.docs:
            #doc_id = doc.get_id()
            #log.info("Got id from ClearingHouse %s", doc_id)
            #guids_in_harvest.add(doc_id)

        new = guids_in_harvest - guids_in_db
        delete = guids_in_db - guids_in_harvest
        change = guids_in_db & guids_in_harvest

        ids = []
        for guid in new:
            doc = json.dumps(harvested[guid])
            obj = HarvestObject(guid=guid, job=harvest_job, content=doc,
                                extras=[HOExtra(key='status', value='new')])
            obj.save()
            ids.append(obj.id)
        for guid in change:
            doc = json.dumps(harvested[guid])
            obj = HarvestObject(guid=guid, job=harvest_job, content=doc,
                                package_id=guid_to_package_id[guid],
                                extras=[HOExtra(key='status', value='change')])
            obj.save()
            ids.append(obj.id)
        for guid in delete:
            obj = HarvestObject(guid=guid, job=harvest_job,
                                package_id=guid_to_package_id[guid],
                                extras=[HOExtra(key='status', value='delete')])
            ids.append(obj.id)
            model.Session.query(HarvestObject).\
                  filter_by(guid=guid).\
                  update({'current': False}, False)
            obj.save()

        if len(ids) == 0:
            self._save_gather_error('No records received from GeoNode', harvest_job)
            return None

        return ids

    def fetch_stage(self, harvest_object):

        # Check harvest object status
        status = self._get_object_extra(harvest_object, 'status')

        if status == 'delete':
            # No need to fetch anything, just pass to the import stage
            return True

        log = logging.getLogger(__name__ + '.GeoNode.fetch')
        log.debug('GeoNodeHarvester fetch_stage for object: %s', harvest_object.id)

        url = harvest_object.source.url
        client = GeoNodeClient(url)

        guid = harvest_object.guid
        content = harvest_object.content
        obj = json.loads(content)
        gnid = obj['id']

        if 'type' not in obj:
            log.error("Bad content in harvest object ID: %d GUID: %s [%s]" % (gnid, guid, content))
            if GEONODE_TYPE in obj:
                # it means it already contains data read in this fetch stage. We were expecting info from the gather stage instead
                log.warning("Harvest object is in the wrong state ID: %d GUID: %s" % (gnid, guid))

            self._save_object_error("Bad content in harvest object ID: %d GUID: %s [%s]" % (gnid, guid, content), harvest_object)
            return False

        objtype = obj['type']

        try:
            if objtype == GEONODE_LAYER_TYPE:
                georesource_json = client.get_layer_json(gnid)
                objdict = json.loads(georesource_json)

            elif objtype == GEONODE_MAP_TYPE:
                georesource_json = client.get_map_json(gnid)
                objdict = json.loads(georesource_json)

                # set into the map object the geoexp configuration blob
                map_blob_json = client.get_map_data(gnid)
                # enriching the json with some more info
                objdict['MAP_DATA'] = map_blob_json

            elif objtype == GEONODE_DOC_TYPE:
                georesource_json = client.get_doc_json(gnid)
                objdict = json.loads(georesource_json)

            else:
                log.error("Unknown GeoNode resource type %s for ID: %d GUID: %s " % (objtype, gnid, guid))
                self._save_object_error("Unknown GeoNode resource type %s for ID: %d GUID: %s " % (objtype, gnid, guid), harvest_object)
                return False

            objdict[GEONODE_TYPE] = objtype
            final_json = json.dumps(objdict)

        except Exception as e:
            log.error('Error getting GeoNode %s ID %d GUID %s [%r]' % (objtype, gnid, guid, e), e)
            self._save_object_error('Error getting GeoNode %s ID %d GUID %s [%r]' % (objtype, gnid, guid, e), harvest_object)
            return False

        if final_json is None:
            self._save_object_error('Empty record for GUID %s type %s' % (guid, objtype), harvest_object)
            return False

        try:
            harvest_object.content = final_json.strip()
            harvest_object.save()
        except Exception as e:
            self._save_object_error('Error saving the harvest object for GUID %s type %s [%r]' %
                                    (guid, objtype, e), harvest_object)
            return False

        log.debug('JSON content saved for %s (size %s)' % (objtype, len(final_json)))
        return True

    def import_stage(self, harvest_object):

        log = logging.getLogger(__name__ + '.import')
        log.debug('Import stage for harvest object: %s' % harvest_object.id)

        if not harvest_object:
            log.error('No harvest object received')
            return False

        self._set_source_config(harvest_object.source.config)

        status = self._get_object_extra(harvest_object, 'status')

        # Get the last harvested object (if any)
        previous_object = Session.query(HarvestObject) \
                          .filter(HarvestObject.guid == harvest_object.guid) \
                          .filter(HarvestObject.current == True) \
                          .first()

        if status == 'delete':
            # Delete package
            context = {'model': model, 'session': model.Session, 'user': self._get_user_name()}

            p.toolkit.get_action('package_delete')(context, {'id': harvest_object.package_id})
            log.info('Deleted package {0} with guid {1}'.format(harvest_object.package_id, harvest_object.guid))

            return True

        if previous_object:
            # Flag previous object as not current anymore
            previous_object.current = False
            previous_object.add()

            # Check if metadata was modified
            # GeoNode does not offer a "latest modified date".
            # Let's compare if any value changed
            content_old = previous_object.content
            content_new = harvest_object.content

            is_modified = content_old != content_new
            prev_job_id = previous_object.job.id
        else:
            is_modified = True
            prev_job_id = None

        # Error if GUID not present
        if not harvest_object.guid:
            self._save_object_error('Missing GUID for object {0}'
                        .format(harvest_object.id), harvest_object, 'Import')
            return False

        log.error('Object GUID:%s is modified: %s' % (harvest_object.guid, is_modified))

        # Let's set the metadata date according to the import time. Not the best choice, since
        # we'd like to set the original metadata date.
        # If geonode provided this info, we could rely on this to find out if a dataset needs to be updated.
        harvest_object.metadata_modified_date = datetime.now()
        harvest_object.add()

        # Build the package dict
        package_dict = self.get_package_dict(harvest_object)
        if not package_dict:
            log.error('No package dict returned, aborting import for object {0}'.format(harvest_object.id))
            return False

        # Create / update the package

        context = {'model': model,
                   'session': model.Session,
                   'user': self._get_user_name(),
                   'extras_as_string': True,
                   'api_version': '2',
                   'return_id_only': True}
        if context['user'] == self._site_user['name']:
            context['ignore_auth'] = True

        # The default package schema does not like Upper case tags
        tag_schema = logic.schema.default_tags_schema()
        tag_schema['name'] = [not_empty, unicode]

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        if status == 'new':
            package_schema = logic.schema.default_create_package_schema()
            package_schema['tags'] = tag_schema
            context['schema'] = package_schema

            # We need to explicitly provide a package ID, otherwise ckanext-spatial
            # won't be be able to link the extent to the package.
            package_dict['id'] = unicode(uuid.uuid4())
            package_schema['id'] = [unicode]

            # Save reference to the package on the object
            harvest_object.package_id = package_dict['id']
            harvest_object.add()
            # Defer constraints and flush so the dataset can be indexed with
            # the harvest object id (on the after_show hook from the harvester
            # plugin)
            Session.execute('SET CONSTRAINTS harvest_object_package_id_fkey DEFERRED')
            model.Session.flush()

            try:
                # package_id = p.toolkit.get_action('package_create')(context, package_dict)
                package_id = self._create_package(context, package_dict, harvest_object)
                log.info('Created new package %s with guid %s' % (package_id, harvest_object.guid))
                self._post_package_create(package_id, harvest_object)
            except p.toolkit.ValidationError as e:
                self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                return False

        elif status == 'change':

            # Check if the document has changed

            if not is_modified:

                # Assign the previous job id to the new object to
                # avoid losing history
                harvest_object.harvest_job_id = prev_job_id
                harvest_object.add()

                harvest_object.metadata_modified_date = previous_object.metadata_modified_date

                # Delete the previous object to avoid cluttering the object table
                previous_object.delete()

                log.info('Document with GUID %s unchanged, skipping...' % (harvest_object.guid))
            else:
                package_schema = logic.schema.default_update_package_schema()
                package_schema['tags'] = tag_schema
                context['schema'] = package_schema

                package_dict['id'] = harvest_object.package_id
                try:
                    #package_id = p.toolkit.get_action('package_update')(context, package_dict)
                    package_id = self._update_package(context, package_dict, harvest_object)
                    log.info('Updated package %s with guid %s' % (package_id, harvest_object.guid))
                    self._post_package_update(package_id, harvest_object)
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

        model.Session.commit()

        return True

    def _create_package(self, context, package_dict, harvest_object):

        json_dict = json.loads(harvest_object.content)
        doc_type = json_dict[GEONODE_TYPE]

        if doc_type == GEONODE_LAYER_TYPE or doc_type == GEONODE_MAP_TYPE:
            package_id = p.toolkit.get_action('package_create')(context, package_dict)

        elif doc_type == GEONODE_DOC_TYPE:
            # doc resources shall be added one by one
            # http://docs.ckan.org/en/ckan-2.2/api.html#ckan.logic.action.create.resource_create

            resources = package_dict.pop('resources', None)

            # create the dataset
            package_id = p.toolkit.get_action('package_create')(context, package_dict)
            log.debug('Base package created: %s' % package_id)

            # add the resources
            for resource in resources:
                log.debug('Adding resource %s to package %s' % (resource['name'], package_id))
                resource['package_id'] = package_id
                created_resource = p.toolkit.get_action('resource_create')(context, resource)
                log.debug('Added resource %s to package %s with uuid %s' % (resource['name'], package_id, created_resource['id']))

        else:
            log.error('Unknown GeoNode type %s' % doc_type)
            return None

        return package_id

    def _update_package(self, context, package_dict, harvest_object):

        json_dict = json.loads(harvest_object.content)
        doc_type = json_dict[GEONODE_TYPE]

        if doc_type == GEONODE_LAYER_TYPE or doc_type == GEONODE_MAP_TYPE:
            package_id = p.toolkit.get_action('package_update')(context, package_dict)

        elif doc_type == GEONODE_DOC_TYPE:
            # Doc resources will be replaced since we don't know if the data changed somehow.
            # 1) update the package, with the new values except the resource
            # 2) update the resource(s) one by one [TODO]
            resources = package_dict.pop('resources', None)

            # create the dataset
            package_id = p.toolkit.get_action('package_update')(context, package_dict)
            log.debug('Base package updated: %s' % package_id)

            # todo: check what's changed in the resources: have previous res been removed?

            # add the resources
            # (we're adding the resources from scratch instead of updating them -- the downside is that we can't have
            # permalinks to resources since the ID will be recreated)
            for resource in resources:
                log.debug('Adding resource %s to package %s' % (resource['name'], package_id))
                resource['package_id'] = package_id
                created_resource = p.toolkit.get_action('resource_create')(context, resource)
                log.debug('Added resource %s to package %s with uuid %s' % (resource['name'], package_id, created_resource['id']))

        else:
            log.error('Unknown GeoNode type %s' % doc_type)
            return None

        return package_id

    def get_package_dict(self, harvest_object):
        '''
        Constructs a package_dict suitable to be passed to package_create or
        package_update.

        If a dict is not returned by this function, the import stage will be cancelled.

        :param harvest_object: HarvestObject domain object (with access to job and source objects)
        :type harvest_object: HarvestObject

        :returns: A dataset dictionary (package_dict)
        :rtype: dict
        '''

        json_dict = json.loads(harvest_object.content)
        doc_type = json_dict[GEONODE_TYPE]

        if doc_type == GEONODE_LAYER_TYPE:
            return self.get_layer_package_dict(harvest_object, harvest_object.content)
        elif doc_type == GEONODE_MAP_TYPE:
            return self.get_map_package_dict(harvest_object, harvest_object.content)
        elif doc_type == GEONODE_DOC_TYPE:
            return self.get_doc_package_dict(harvest_object, harvest_object.content)
        else:
            log.error('Unknown GeoNode type %s' % doc_type)
            return None

    def get_layer_package_dict(self, harvest_object, json_layer):

        layer = Layer(json_layer)

        package_dict, extras = self.get_resource_package_dict(harvest_object, layer)

        # Add WMS resource
        resource = {}
        resource['format'] = 'wms'
        resource['url'] = self.source_config['geoserver_url'] + "/wms"
        resource['name'] = "%s:%s" % (layer.workspace(), layer.name())
        resource['description'] = p.toolkit._('WMS resource')
        package_dict['resources'].append(resource)

        extras['is_vector'] = layer.is_vector()

        self._addExtras(package_dict, extras)

        return package_dict

    def get_map_package_dict(self, harvest_object, json_map):

        geomap = Map(json_map)

        package_dict, extras = self.get_resource_package_dict(harvest_object, geomap)

        # Add WMS resource
        resource = {}
        resource['format'] = 'map'
        resource['url'] = '%s/maps/%s/wmc' % (harvest_object.source.url, geomap.id())
        resource['name'] = 'Map'
        resource['description'] = p.toolkit._('Full map context')
        resource['map_data'] = geomap.map_data()

        package_dict['resources'].append(resource)

        self._addExtras(package_dict, extras)

        return package_dict

    def get_doc_package_dict(self, harvest_object, json_map):

        doc = Doc(json_map)

        package_dict, extras = self.get_resource_package_dict(harvest_object, doc)

        # Add WMS resource
        resource = {}
        resource['format'] = doc.extension()
        # Not sure about this: we're creating a resource in CKAN, so we'll have to create a URL for this.
        # "url" is mandatory, and not providing it will raise a Validation Error
        resource['url'] = '%s/documents/%s/download' % (harvest_object.source.url, doc.id())
        resource['source_url'] = '%s/documents/%s/download' % (harvest_object.source.url, doc.id())

        resource['name'] = doc.doc_file()
        resource['description'] = doc.doc_type()

        # download doc content and add it in the resource
        # TODO: download should only be performed when needed: now we do it also when the metadata has not changed

        baseurl = harvest_object.source.url
        client = GeoNodeClient(baseurl)
        doc_content = client.get_document_download(doc.id())

        log.info('Downloaded document "%s" (size %d)' % (doc.doc_file(), len(doc_content)))

        storage = MockFieldStorage(doc_content, doc.doc_file())
        resource['upload'] = storage

        #
        package_dict['resources'].append(resource)

        self._addExtras(package_dict, extras)

        return package_dict

    def get_resource_package_dict(self, harvest_object, georesource):
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
        #for tag in doc.get_keywords():
            #tag = tag[:50] if len(tag) > 50 else tag
            #tags.append({'name': tag})

        package_dict = {
            'title': georesource.title(),
            'notes': georesource.abstract(),
            'tags': tags,
            'resources': [],
        }

        # We need to get the owner organization (if any) from the harvest
        # source dataset
        source_dataset = model.Package.get(harvest_object.source.id)
        if source_dataset.owner_org:
            package_dict['owner_org'] = source_dataset.owner_org

        # Package name
        package = harvest_object.package
        if package is None or package.title != georesource.title():
            name = self._gen_new_name(georesource.title())
            if not name:
                name = self._gen_new_name(georesource.name())
            if not name:
                raise Exception('Could not generate a unique name from the title or the resource name. Please choose a more unique title.')
            package_dict['name'] = name
        else:
            package_dict['name'] = package.name

        extras = {
            'guid': harvest_object.guid,
            'author': georesource.owner(),
#            'publisher':
#            'publication_place':
#            'publication_date':
        }

        if georesource.date_type() == 'publication':
            extras['publication_date'] = georesource.date()

        if georesource.is_spatial():

            if georesource.srid():
                extras['spatial-reference-system'] = georesource.srid()

            ## Some of the extras we may want to add in the future:
                ## Essentials
                #'spatial-reference-system',
                #'guid',
                ## Usefuls
                #'dataset-reference-date',
                #'metadata-language',  # Language
                #'metadata-date',  # Released
                #'coupled-resource',
                #'contact-email',
                #'frequency-of-update',
                #'spatial-data-service-type',
                #extras['progress'] = ''
                #extras['resource-type'] = ''
                #extras['licence']
                #extras['access_constraints']
                #extras['graphic-preview-file']
                #extras['graphic-preview-description']
                #extras['graphic-preview-type']
                #extras['responsible-party'] = [{'name': k, 'roles': v} for k, v in parties.iteritems()]

            if georesource.thumbnail():
                extras['graphic-preview-file'] = georesource.thumbnail()

            # Set up bounding box

            extras['bbox-east-long'] = georesource.x1()
            extras['bbox-north-lat'] = georesource.y1()
            extras['bbox-south-lat'] = georesource.y0()
            extras['bbox-west-long'] = georesource.x0()

            try:
                xmin = float(georesource.x0())
                xmax = float(georesource.x1())
                ymin = float(georesource.y0())
                ymax = float(georesource.y1())
            except ValueError as e:
                self._save_object_error('Error parsing bounding box value: {0}'.format(str(e)),
                                        harvest_object, 'Import')
            else:
                # Construct a GeoJSON extent so ckanext-spatial can register the extent geometry

                # Some publishers define the same two corners for the bbox (ie a point),
                # that causes problems in the search if stored as polygon
                if xmin == xmax or ymin == ymax:
                    extent_string = Template('{"type": "Point", "coordinates": [$x, $y]}').substitute(
                        x=xmin, y=ymin
                    )
                    self._save_object_error('Point extent defined instead of polygon',
                                     harvest_object, 'Import')
                else:
                    extent_string = self.extent_template.substitute(
                        xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
                    )

                extras['spatial'] = extent_string.strip()

        return package_dict, extras

    def _post_package_create(self, package_id, harvest_object):
        pass

    def _post_package_update(self, package_id, harvest_object):
        pass

    def _addExtras(self, package_dict, extras):

        extras_as_dict = []
        for key, value in extras.iteritems():
            if isinstance(value, (list, dict)):
                extras_as_dict.append({'key': key, 'value': json.dumps(value)})
            else:
                extras_as_dict.append({'key': key, 'value': value})

        package_dict['extras'] = extras_as_dict

    def _set_source_config(self, config_str):
        '''
        Loads the source configuration JSON object into a dict for
        convenient access
        '''
        if config_str:
            self.source_config = json.loads(config_str)
            log.debug('Using config: %r' % self.source_config)
        else:
            self.source_config = {}

    def _get_object_extra(self, harvest_object, key):
        '''
        Helper function for retrieving the value from a harvest object extra,
        given the key
        '''
        for extra in harvest_object.extras:
            if extra.key == key:
                return extra.value
        return None

    def _get_user_name(self):
        '''
        Returns the name of the user that will perform the harvesting actions
        (deleting, updating and creating datasets)

        By default this will be the internal site admin user. This is the
        recommended setting, but if necessary it can be overridden with the
        `ckanext.spatial.harvest.user_name` config option, eg to support the
        old hardcoded 'harvest' user:

           ckanext.spatial.harvest.user_name = harvest

        '''
        if self._user_name:
            return self._user_name

        self._site_user = p.toolkit.get_action('get_site_user')({'model': model, 'ignore_auth': True}, {})

        config_user_name = config.get('ckanext.spatial.harvest.user_name')
        if config_user_name:
            self._user_name = config_user_name
        else:
            self._user_name = self._site_user['name']

        return self._user_name