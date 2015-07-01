import logging

import urllib2

import tempfile

log = logging.getLogger(__name__)

WFS_FORMAT_CSV = "csv"

WFS_VERSION_200 = "2.0.0"


def get_wfs_getfeatures_url(gsbaseurl, typename, version=WFS_VERSION_200, output_format=WFS_FORMAT_CSV):
    return gsbaseurl + "/wfs?service=WFS&typename=" \
        + typename + "&outputFormat=" \
        + output_format + "&version=" \
        + version + "&request=GetFeature"


def load_wfs_getfeatures(gsbaseurl, typename, outputfile=None, version=WFS_VERSION_200, output_format=WFS_FORMAT_CSV):

    url = gsbaseurl + "/wfs?service=WFS&typename=" \
        + typename + "&outputFormat=" \
        + output_format + "&version=" \
        + version + "&request=GetFeature"

    log.debug('Retrieve WFS GetFeature from %s into %s', url, outputfile)
    log.debug('Retrieve GetFeature for layer: %r', typename)
    log.debug('GetFeature output format: %r', output_format)
    log.debug('GetFeature version: %r', version)

    # TODO: loop to retrieve all the features
    # TODO: stream the output to the file

    http_request = urllib2.Request(url)
    http_response = urllib2.urlopen(http_request)

    content = http_response.read()

    if not outputfile:
        outputfile = tempfile.TemporaryFile()

    outputfile.write(content)
    outputfile.seek(0)

    return outputfile
