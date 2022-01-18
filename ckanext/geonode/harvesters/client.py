# -*- coding: utf-8 -*-
import json
import logging

from urllib.request import urlopen

from ckanext.geonode.harvesters import GeoNodeType

log = logging.getLogger(__name__)


class GeoNodeClient(object):

    def __init__(self, baseurl):
        self.baseurl = baseurl.rstrip('/')

    def get_maps(self):
        return self.get_resources(GeoNodeType.MAP_TYPE)

    def get_layers(self):
        return self.get_resources(GeoNodeType.LAYER_TYPE)

    def get_documents(self):
        return self.get_resources(GeoNodeType.DOC_TYPE)

    def get_resources(self, res_type: GeoNodeType):
        ''' return geonode resource json '''

        url = f'{self.baseurl}/api/v2/{res_type.api_path}/'

        while True:
            log.debug('Retrieving %s at GeoNode URL %s', res_type.config_name, url)
            response = urlopen(url).read()
            json_content = json.loads(response)

            url = json_content['links']['next']

            objects = json_content[res_type.json_resource_list]
            for res in objects:
                lid = res['pk']
                luuid = res['uuid']
                ltitle = res['title']
                log.info(f'Found {res_type.json_resource_type} {luuid} id:{lid} "{ltitle}"')
                yield res

            if url is None:
                break


    # def get_layer_json(self, id):
    #     return self._get_resource_json(id, RESTYPE_LAYER)
    #
    # def get_map_json(self, id):
    #     return self._get_resource_json(id, RESTYPE_MAP)
    #
    # def get_doc_json(self, id):
    #     return self._get_resource_json(id, RESTYPE_DOC)
    #
    # def _get_resource_json(self, id, res_type):
    #     ''' return a resource (map or layer) '''
    #     log.debug(f'Retrieving {res_type} id:{id}')
    #     url = f'{self.baseurl}/api/{res_type}/{id}/'
    #     response = urlopen(url)
    #     return response.read()
    #
    # def get_map_data(self, id):
    #     log.debug('Retrieve blob data for map #%d', id)
    #
    #     url = f'{self.baseurl}/maps/{id}/data'
    #     response = urlopen(url)
    #     return response.read()

    def get_document_download(self, id):
        """
        Download the full document from geonode.
        TODO: at the moment we're loading the doc in memory: it should be streamed to a file.
        """
        log.debug('Retrieve blob data for document #%d', id)

        url = f'{self.baseurl}/documents/{id}/download'
        response = urlopen(url)
        return response.read()
