# -*- coding: utf-8 -*-
import logging

import urllib2

from ckan.common import json

log = logging.getLogger(__name__)

RESTYPE_LAYER = "layers"
RESTYPE_MAP = "maps"


class GeoNodeClient(object):

    def __init__(self, baseurl):

        self.baseurl = baseurl

    def get_maps(self):
        return self._get_resources(RESTYPE_MAP)

    def get_layers(self):
        return self._get_resources(RESTYPE_LAYER)

    def _get_resources(self, resType):
        ''' return id,uuid,title '''

        # todo : transform into a generator using paged retrieving in API

        url = '%s/api/%s/' % (self.baseurl, resType)

        log.info('Retrieving %s at GeoNode URL %s', (resType, url))
        request = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(), urllib2.HTTPRedirectHandler())

        response = opener.open(request)
        content = response.read()

        json_content = json.loads(content)

        objects = json_content['objects']
        ret = []
        for layer in objects:
            lid = layer['id']
            luuid = layer['uuid']
            ltitle = layer['title']

            log.info('%s: found %s %s %s' % (resType, lid, luuid, ltitle))

            ret.append({'id': lid, 'uuid': luuid, 'title': ltitle})

        return ret

    def get_layer_json(self, id):
        return self._get_resource_json(id, RESTYPE_LAYER)

    def get_map_json(self, id):
        return self._get_resource_json(id, RESTYPE_MAP)

    def _get_resource_json(self, id, resType):
        ''' return a resource (map or layer) '''

        url = '%s/api/%s/%d/' % (self.baseurl, resType, id)

        log.info('Connecting to GeoNode at %s', url)
        request = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(), urllib2.HTTPRedirectHandler())

        response = opener.open(request)
        content = response.read()

        return content

    def get_map_data(self, id):

        url = '%s/maps/%d/data' % (self.baseurl, id)

        log.info('Retrieve blob data for map #%d', id)
        request = urllib2.Request(url)
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(), urllib2.HTTPRedirectHandler())

        response = opener.open(request)
        content = response.read()

        return content

