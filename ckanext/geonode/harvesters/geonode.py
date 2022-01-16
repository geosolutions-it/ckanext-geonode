import json
import shapely
import shapely.wkt as wkt
import logging
import uuid
from tempfile import SpooledTemporaryFile
from string import Template
from datetime import datetime

from ckan import logic
from ckan.logic import NotFound, get_action
from ckan import model
from ckan.model import Session
from ckan import plugins as p

from ckan.lib.navl.validators import not_empty
from ckan.plugins.core import SingletonPlugin, implements

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.harvesters.base import HarvesterBase
from ckanext.harvest.model import HarvestObject, HarvestObjectExtra as HOExtra

from ckanext.geonode.harvesters.client import GeoNodeClient
from ckanext.geonode.harvesters.mappers.base import map_resource
from ckanext.geonode.harvesters.downloader import GeonodeDataDownloader, WFSCSVDownloader
from ckanext.geonode.harvesters import (
    CONFIG_GEOSERVERURL, CONFIG_IMPORT_FIELDS, CONFIG_KEYWORD_MAPPING, CONFIG_GROUP_MAPPING,
    CONFIG_GROUP_MAPPING_FIELDNAME, GeoNodeType,
    RESOURCE_DOWNLOADER, TEMP_FILE_THRESHOLD_SIZE, CONFIG_IMPORT_TYPES,

)
from ckanext.geonode.model.types import Layer, Map, Doc, GeoNodeResourceLink, GeoNodeResource


log = logging.getLogger(__name__)
config = p.toolkit.config


class GeoNodeHarvester(HarvesterBase, SingletonPlugin):
    """
        A Harvester for GeoNode's layers, map, docs.
    """
    implements(IHarvester)

    _user_name = None

    source_config = {}
    geoserver_url = None


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

        log = logging.getLogger(__name__ + '.geonode.config')

        try:
            source_config_obj = json.loads(source_config)

            # GeoNode does not expose the internal GeoServer URL, so we have to config it on its own
            # if not CONFIG_GEOSERVERURL in source_config_obj:
            #     raise ValueError('geoserver_url is mandatory')
            #
            # if not isinstance(source_config_obj[CONFIG_GEOSERVERURL], str):
            #     raise ValueError('geoserver_url should be a string')

            if 'import_wfs_as_csv' in source_config_obj:
                if not source_config_obj['import_wfs_as_csv'] in ['true', 'false']:
                    raise ValueError('import_wfs_as_csv should be either true or false')

            if 'import_wfs_as_wfs' in source_config_obj:
                if not isinstance(source_config_obj['import_wfs_as_wfs'], bool):
                    raise ValueError('import_wfs_as_wfs should be either true or false')

            if CONFIG_IMPORT_FIELDS in source_config_obj:
                if not isinstance(source_config_obj[CONFIG_IMPORT_FIELDS], list):
                    raise ValueError('%s should be a list', CONFIG_IMPORT_FIELDS)

            self.check_mapping(CONFIG_KEYWORD_MAPPING, source_config_obj, list)
            self.check_mapping(CONFIG_GROUP_MAPPING, source_config_obj, str)
            self.check_mapping(CONFIG_IMPORT_TYPES, source_config_obj, bool,
                               lambda x: x in (GeoNodeType.get_config_names()))

            if CONFIG_GROUP_MAPPING in source_config_obj and CONFIG_GROUP_MAPPING_FIELDNAME not in source_config_obj:
                raise ValueError('%s needs also %s to be defined', CONFIG_GROUP_MAPPING, CONFIG_GROUP_MAPPING_FIELDNAME)

        except ValueError as e:
            log.warning("Config parsing error: %r", e)
            raise e

        return json.dumps(source_config_obj)

    def check_mapping(self, key, source_config_obj, datatype, key_validator=None):
        if key in source_config_obj:
            mapping = source_config_obj[key]
            if not isinstance(mapping, dict):
                raise ValueError('%s should be a dict' % key)
            for k, v in mapping.items():
                if key_validator:
                    if not key_validator(k):
                        raise ValueError('"{key}" key is not valid for config "{configkey}"'
                                         .format(configkey=key, key=k))
                else:
                    # no custom validator, we only need it's a string
                    if not isinstance(k, str):
                        raise ValueError('%s keys should be strings' % key)
                if type(v) != datatype:
                    raise ValueError('%s values should be %r' % (key, datatype))

    def gather_stage(self, harvest_job):
        log = logging.getLogger(__name__ + '.geonode.gather')
        log.debug('GeoNode gather_stage for job: %r', harvest_job)
        # Get source URL
        url = harvest_job.source.url

        self._set_source_config(harvest_job.source.config)

        try:
            log.info('Connecting to GeoNode at %s', url)

            query = model.Session.query(HarvestObject.guid, HarvestObject.package_id). \
                filter(HarvestObject.current == True). \
                filter(HarvestObject.harvest_source_id == harvest_job.source.id)

            guid_to_package_id = {}
            for guid, package_id in query:
                guid_to_package_id[guid] = package_id

            guids_in_db = list(guid_to_package_id.keys())

            ho_ids = []

            client = GeoNodeClient(url)

            # dict guid: layer
            harvested = []

            cnt_upd = 0
            cnt_add = 0

            for geonode_type in GeoNodeType:

                if CONFIG_IMPORT_TYPES in self.source_config:
                    # if import config is there, only import defined types
                    import_types = self.source_config[CONFIG_IMPORT_TYPES]
                    if not import_types.get(geonode_type.config_name, False):
                        log.info(f'Skipping resource type: {geonode_type}')
                        continue

                for obj in client.get_resources(geonode_type):
                    uuid = obj['uuid']
                    doc = json.dumps(obj)
                    if uuid in guids_in_db:
                        ho = HarvestObject(guid=uuid, job=harvest_job, content=doc,
                                           package_id=guid_to_package_id[uuid],
                                           extras=[HOExtra(key='status', value='change')])
                        action = 'UPDATE'
                        cnt_upd = cnt_upd + 1
                    else:
                        ho = HarvestObject(guid=uuid, job=harvest_job, content=doc,
                                           extras=[HOExtra(key='status', value='new')])
                        action = 'ADD'
                        cnt_add = cnt_add + 1

                    ho.save()
                    ho_ids.append(ho.id)
                    harvested.append(uuid)
                    log.info(f'Queued {geonode_type.config_name} uuid {uuid} for {action}')

        except Exception as e:
            self._save_gather_error('Error harvesting GeoNode: %s' % e, harvest_job)
            return None

        delete = set(guids_in_db) - set(harvested)

        log.info(f'Found {len(harvested)} objects,  {cnt_add} new, {cnt_upd} to update, {len(delete)} to remove')

        for guid in delete:
            ho = HarvestObject(guid=guid, job=harvest_job,
                               package_id=guid_to_package_id[guid],
                               extras=[HOExtra(key='status', value='delete')])
            model.Session.query(HarvestObject). \
                filter_by(guid=guid). \
                update({'current': False}, False)
            ho.save()
            ho_ids.append(ho.id)

        if len(harvested) == 0 and len(delete) == 0:
            self._save_gather_error('No records received from GeoNode', harvest_job)
            return None

        return ho_ids

    def fetch_stage(self, harvest_object):

        return True  # objects fetched in gather stage

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
        tag_schema['name'] = [not_empty, str]

        # Flag this object as the current one
        harvest_object.current = True
        harvest_object.add()

        if status == 'new':
            package_schema = logic.schema.default_create_package_schema()
            package_schema['tags'] = tag_schema
            context['schema'] = package_schema

            # We need to explicitly provide a package ID, otherwise ckanext-spatial
            # won't be be able to link the extent to the package.
            package_dict['id'] = str(uuid.uuid4())
            package_schema['id'] = [str]

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

                log.info('Document with GUID %s unchanged, skipping...', harvest_object.guid)
                model.Session.commit()
                return "unchanged"
            else:
                package_schema = logic.schema.default_update_package_schema()
                package_schema['tags'] = tag_schema
                context['schema'] = package_schema

                package_dict['id'] = harvest_object.package_id
                try:
                    # package_id = p.toolkit.get_action('package_update')(context, package_dict)
                    package_id = self._update_package(context, package_dict, harvest_object)
                    log.info('Updated package %s with guid %s', package_id, harvest_object.guid)
                    self._post_package_update(package_id, harvest_object)
                except p.toolkit.ValidationError as e:
                    self._save_object_error('Validation Error: %s' % str(e.error_summary), harvest_object, 'Import')
                    return False

        model.Session.commit()

        return True

    def _create_package(self, context, package_dict, harvest_object):

        # Resources with data to be downloaded will be added later
        # http://docs.ckan.org/en/ckan-2.2/api.html#ckan.logic.action.create.resource_create
        resources = package_dict.pop('resources', None)
        downloadable_resources = []
        normal_resources = []
        for resource in resources:
            if resource.get(RESOURCE_DOWNLOADER, None):
                downloadable_resources.append(resource)
            else:
                normal_resources.append(resource)

        if len(normal_resources):
            package_dict['resources'] = normal_resources

        package_id = p.toolkit.get_action('package_create')(context, package_dict)

        # Handle data downloads
        for resource in downloadable_resources:
            resource['package_id'] = package_id
            log.info('Handling download data for resource %s in package %s', resource['name'], package_id)
            downloader = resource.pop(RESOURCE_DOWNLOADER)

            with SpooledTemporaryFile(max_size=TEMP_FILE_THRESHOLD_SIZE) as f:
                fieldStorage = downloader.download(f)

                resource['upload'] = fieldStorage
                log.info('Create resource %s in package %s', resource['name'], package_id)
                created_resource = p.toolkit.get_action('resource_create')(context, resource)
                log.debug('Added resource %s to package %s with uuid %s', resource['name'], package_id,
                          created_resource['id'])

        return package_id

    def _update_package(self, context, package_dict, harvest_object):

        # Resources will be replaced since we don't know if the data changed somehow.
        # 1) update the package, with the new values except the resource that need downloading
        # 2) update the resource(s) one by one
        # shoud we remove by hands the old resource data from the datastore? TODO

        resources = package_dict.pop('resources', None)
        downloadable_resources = []
        normal_resources = []
        for resource in resources:
            if resource.get(RESOURCE_DOWNLOADER, None):
                downloadable_resources.append(resource)
            else:
                normal_resources.append(resource)

        if len(normal_resources):
            package_dict['resources'] = normal_resources

        package_id = p.toolkit.get_action('package_update')(context, package_dict)

        # Handle data downloads

        # TODO: check what's changed in the resources: have previous res been removed?

        # add the resources
        # (we're adding the resources from scratch instead of updating them -- the downside is that we can't have
        # permalinks to resources since the ID will be recreated)

        for resource in downloadable_resources:
            resource['package_id'] = package_id
            log.info('Handling download data for resource %s in package %s' % (resource['name'], package_id))
            downloader = resource.pop(RESOURCE_DOWNLOADER)

            with SpooledTemporaryFile(max_size=TEMP_FILE_THRESHOLD_SIZE) as f:
                fieldStorage = downloader.download(f)
                resource['upload'] = fieldStorage
                log.info('Create resource %s in package %s', resource['name'], package_id)
                created_resource = p.toolkit.get_action('resource_create')(context, resource)
                log.debug('Added resource %s to package %s with uuid %s', resource['name'], package_id,
                          created_resource['id'])

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

        package_dict, extras = map_resource(harvest_object, self.source_config)
        self._addExtras(package_dict, extras)
        return package_dict

    def _post_package_create(self, package_id, harvest_object):
        pass

    def _post_package_update(self, package_id, harvest_object):
        pass

    def _addExtras(self, package_dict, extras):

        extras_as_dict = []
        for key, value in extras.items():
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

    def _get_config_value(self, key, default):
        if key in self.source_config:
            # trivial heuristics
            if 'true' == self.source_config[key]:
                return True
            if 'false' == self.source_config[key]:
                return False
            return self.source_config[key]
        else:
            return default

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
