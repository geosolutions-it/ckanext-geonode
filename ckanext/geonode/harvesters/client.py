# -*- coding: utf-8 -*-
import json
import logging

from urllib.request import urlopen

log = logging.getLogger(__name__)

RESTYPE_LAYER = "layers"
RESTYPE_MAP = "maps"
RESTYPE_DOC = "documents"


class GeoNodeClient(object):

    def __init__(self, baseurl):
        self.baseurl = baseurl

    def get_maps(self):
        return self._get_resources(RESTYPE_MAP)

    def get_layers(self):
        return self._get_resources(RESTYPE_LAYER)

    def get_documents(self):
        return self._get_resources(RESTYPE_DOC)

    def _get_resources(self, res_type):
        ''' return id,uuid,title '''

        # todo : transform into a generator using paged retrieving in API
        url = '%s/api/%s/' % (self.baseurl, res_type)

        log.debug('Retrieving %s at GeoNode URL %s', res_type, url)
        response = urlopen(url).read()
        json_content = json.loads(response)

        objects = json_content['objects']
        ret = []
        for res in objects:
            lid = res['id']
            luuid = res['uuid']
            ltitle = res['title']

            log.info('%s: found id:%s uuid:%s "%s"', res_type, lid, luuid, ltitle)
            ret.append({'id': lid, 'uuid': luuid, 'title': ltitle})

        return ret

    def get_layer_json(self, id):
        return self._get_resource_json(id, RESTYPE_LAYER)

    def get_map_json(self, id):
        return self._get_resource_json(id, RESTYPE_MAP)

    def get_doc_json(self, id):
        return self._get_resource_json(id, RESTYPE_DOC)

    def _get_resource_json(self, id, res_type):
        ''' return a resource (map or layer) '''
        log.debug(f'Retrieving {res_type} id:{id}')
        url = f'{self.baseurl}/api/{res_type}/{id}/'
        response = urlopen(url)
        return response.read()

    def get_map_data(self, id):
        log.debug('Retrieve blob data for map #%d', id)

        url = f'{self.baseurl}/maps/{id}/data'
        response = urlopen(url)
        return response.read()

    def get_document_download(self, id):
        """
        Download the full document from geonode.
        TODO: at the moment we're loading the doc in memory: it should be streamed to a file.
        """
        log.debug('Retrieve blob data for document #%d', id)

        url = f'{self.baseurl}/documents/{id}/download'
        response = urlopen(url)
        return response.read()
