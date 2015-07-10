# -*- coding: utf-8 -*-

from ckanext.geonode.harvesters import utils
from ckanext.geonode.harvesters.client import GeoNodeClient

from cgi import FieldStorage
import os
import logging

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

log = logging.getLogger(__name__)


class MockFieldStorage(FieldStorage):
    """
    Class used to pass the resource data to create_resource.
    It expects an HTTP POST (or GET) method, so we have to mimick its content.
    """

    def __init__(self, filename, content=None, datafile=None):
        if not content and not datafile:
            raise ValueError('At least one of content or datafile should be defined')

        if content and datafile:
            raise ValueError('Either content or datafile should be defined')

        env = dict()
        env['REQUEST_METHOD'] = 'DUMMY'

        FieldStorage.__init__(self, fp=StringIO(content) if content else datafile, environ=env)
        # FieldStorage is declared as an old-style class, so super() cannot be used
        #super(MockFieldStorage, self).__init__(fp=StringIO(content))
        self.filename = filename


class Downloader(object):
    pass


class GeonodeDataDownloader(Downloader):

    def __init__(self, url, doc_id, filename):
        self.url = url
        self.doc_id = doc_id
        self.filename = filename

    def download(self, _file_unused):
        client = GeoNodeClient(self.url)
        doc_content = client.get_document_download(self.doc_id)

        log.info('Downloaded document "%s" (size %d)', self.filename, len(doc_content))

        storage = MockFieldStorage(self.filename, content=doc_content)

        return storage


class WFSCSVDownloader(Downloader):

    def __init__(self, url, typename, filename):
        self.url = url
        self.typename = typename
        self.filename = filename

    def download(self, file):

        utils.load_wfs_getfeatures(self.url, self.typename, outputfile=file)
        log.info('Downloaded document "%s" (size %d)', self.filename, self._file_size(file))

        storage = MockFieldStorage(self.filename, datafile=file)

        return storage

    def _file_size(self, f):
        old_file_position = f.tell()
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(old_file_position, os.SEEK_SET)
        return size
