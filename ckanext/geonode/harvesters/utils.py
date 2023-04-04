import datetime
import logging
import tempfile
from urllib.request import urlopen

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

    http_response = urlopen(url)

    content = http_response.read()

    if not outputfile:
        outputfile = tempfile.TemporaryFile()

    outputfile.write(content)
    outputfile.seek(0)

    return outputfile


def format_date(value, format='%Y-%m-%d'):
    dateformats = (
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S.%f%zZ',
        '%Y-%m-%d %H:%M:%S',
        # '2021-12-17T11:41:54.854696+00:00Z'
        # '%d-%m-%Y %H:%M:%S',
    )

    date = None
    for dateformat in dateformats:
        try:
            date = datetime.datetime.strptime(value, dateformat)
        except ValueError:
            continue

        try:
            date = date.strftime(format)
            return date
        except ValueError as err:
            log.error(f'Cannot reformat "{date}" using format "{format}"')
            return None

    log.error(f'Cannot parse "{value}"')
    return None


def tags_trimmer(default_limit=100):
    '''
    If the value is over a limit, it changes it to the limit. The limit is
    defined by a configuration option, or if that is not set, a given int
    default_limit.
    '''
    def callable(key, data, errors, context):

        if len(data.get(key)) > default_limit:
            data[key] = data[key][:default_limit]

    return callable