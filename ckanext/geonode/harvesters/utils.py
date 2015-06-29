import logging

import ckan
import urllib2

log = logging.getLogger(__name__)

def get_wfs_document(file_path, gsbaseurl, typename, version, output_format):
	url = gsbaseurl + "/wfs?service=WFS&typename=" + typename + "&outputFormat=" + output_format + "&version=" + version + "&request=GetFeature"
	
        log.info('Retrieve GetFeature for layer: %r', typename)
        log.info('GetFeature output format: %r', output_format)
        log.info('GetFeature version: %r', version)
	
        http_request = urllib2.Request(url)
        http_response = urllib2.urlopen(http_request)

        content = http_response.read()
	
        file = open(file_path, "w")
        file.write(content)
        file.close()
	
        return file
