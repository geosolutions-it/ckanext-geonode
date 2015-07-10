# -*- coding: utf-8 -*-
import logging
import os

log = logging.getLogger(__name__)

from ckan.common import json


class GeoNodeResource(object):
    """"
    Generic resource from GeoNode.
    Can be a Layer, a Map or a Document.
    """

    _dict = None

    def __init__(self, json_string):
        self._dict = json.loads(json_string)

    def get(self, key):
        return self._dict.get(key)

    def is_spatial(self):
        return False

    def id(self):
        return self._dict['id']

    def title(self):
        return self._dict['title']

    def abstract(self):
        return self._dict['abstract']

    def purpose(self):
        return self._dict['purpose']

    # e.g. "csw_insert_date" : "2015-05-12T12:56:48.407915",
    def insertdate(self):
        return self._dict['csw_insert_date']

    def date(self):
        return self._dict['date']

    def date_type(self):
        return self._dict['date_type']

    def time_start(self):
        return self._dict['temporal_extent_start']

    def time_end(self):
        return self._dict['temporal_extent_end']

    def owner(self):
        owner = self._dict['owner']
        if owner['first_name'] and owner['last_name']:
            return "%s %s" % (owner['first_name'], owner['last_name'])
        elif not owner['first_name'] and not owner['last_name']:
            return '[%s]' % owner['username']
        else:
            return '%s [%s]' % (owner['first_name'] or owner['last_name'], owner['username'])

    def owner_email(self):
        owner = self._dict['owner']
        return owner['email'] or None


class GeoResource(GeoNodeResource):
    """
    A spatial resource from GeoNode, i.e. a Layer or a Map.
    """

    def __init__(self, json_string):
        super(GeoResource, self).__init__(json_string)

    def is_spatial(self):
        return True

    def thumbnail(self):
        return self._dict['thumbnail_url']

    def srid(self):
        return self._dict['srid']

    def x0(self):
        return self._dict['bbox_x0']

    def x1(self):
        return self._dict['bbox_x1']

    def y0(self):
        return self._dict['bbox_y0']

    def y1(self):
        return self._dict['bbox_y1']


class Layer(GeoResource):

    def __init__(self, json_string):
        super(Layer, self).__init__(json_string)

    def workspace(self):
        return self._dict['workspace']

    def name(self):
        return self._dict['name']

    def store(self):
        return self._dict['store']

    def is_vector(self):
        return self._dict['storeType'] == 'dataStore'


class Map(GeoResource):

    def __init__(self, json_string):
        super(Map, self).__init__(json_string)

    def projection(self):
        return self._dict['projection']

    def center_x(self):
        ''' center coordinates are in the projected system '''
        return self._dict['center_x']

    def center_y(self):
        ''' center coordinates are in the projected system '''
        return self._dict['center_y']

    def map_data(self):
        return self._dict['MAP_DATA']


class Doc(GeoNodeResource):

    def __init__(self, json_string):
        super(Doc, self).__init__(json_string)

    def doc_file(self):
        path = self._dict['doc_file']
        return os.path.basename(path)

    def doc_type(self):
        return self._dict['doc_type']

    def extension(self):
        return self._dict['extension']
