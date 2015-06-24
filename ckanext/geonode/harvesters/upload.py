# -*- coding: utf-8 -*-

from cgi import FieldStorage
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

    def __init__(self, content, filename):
        env = dict()
        env['REQUEST_METHOD'] = 'DUMMY'

        FieldStorage.__init__(self, fp=StringIO(content), environ=env)
        # FieldStorage is declared as an old-style class, so super() cannot be used
        #super(MockFieldStorage, self).__init__(fp=StringIO(content))
        self.filename = filename



