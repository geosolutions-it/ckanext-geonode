import json
import logging
import os
import pytest
import unittest

from jsonpath_ng import jsonpath, parse

from ckan.model.meta import Session

from ckan.tests import helpers, factories

from ckanext.geonode.harvesters.mappers.dynamic import parse_dynamic, validate_config


class DynamicMapperTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_tkeyword_to_value_tag(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping': [
                {
                    'filters': [
                        "resource_type=='map'",
                        "tkeywords[?name=='nz' && thesaurus.uri == 'http://inspire.ec.europa.eu/theme']"
                    ],
                    'actions': [
                        {
                            'value': 'Rischio naturale',
                            'destination': 'tag'
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_dynamic(config, geonode_map, pkg_dict, extras)

        tags = pkg_dict['tags']
        logging.warning(f"TAGS {tags}")
        self.assertEqual(1, len(tags))
        self.assertEqual('Rischio naturale', tags[0]['name'])

    def test_nested_filter(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            "dynamic_mapping": [
                {
                    "filters": ["tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme']"],
                    "actions": [
                        {
                            "destination": "tag",
                            "value": "INSPIRE",
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_dynamic(config, geonode_map, pkg_dict, extras)

        tags = pkg_dict['tags']
        self.assertEqual(1, len(tags))
        self.assertEqual('INSPIRE', tags[0]['name'])


    def test_tkeyword_source_multiple_tag(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            "dynamic_mapping": [
                {
                    "filters": [],
                    "actions": [
                        {
                            "source": "tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme'].name",
                            "destination": "tag"
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_dynamic(config, geonode_map, pkg_dict, extras)

        tags = pkg_dict['tags']
        self.assertEqual(2, len(tags))
        tags_content = set([tag['name'] for tag in tags])
        self.assertSetEqual(set(('nz', 'hb')), tags_content)


    def test_tkeyword_source_multiple_extras_from_empty(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping': [
                {
                    'filters': [],
                    'actions': [
                        {
                            "source": "tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme'].name",
                            'destination': 'foobar'
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_dynamic(config, geonode_map, pkg_dict, extras)

        self.assertEqual(1, len(extras))
        self.assertTrue(isinstance(extras['foobar'], list))
        self.assertEqual(2, len(extras['foobar']))
        self.assertSetEqual(set(('nz', 'hb')), set(extras['foobar']))

    def test_tkeyword_source_multiple_extras_populated(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping': [
                {
                    'filters': [],
                    'actions': [
                        {
                            "source": "tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme'].name",
                            'destination': 'foobar'
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': []
        }
        extras = {
            'already': 'here'
        }

        validate_config(config)
        package_dict, extras = parse_dynamic(config, geonode_map, pkg_dict, extras)

        self.assertEqual(2, len(extras))
        self.assertTrue(isinstance(extras['foobar'], list))
        self.assertTrue(isinstance(extras['already'], str))
        self.assertEqual(2, len(extras['foobar']))
        self.assertSetEqual(set(('nz', 'hb')), set(extras['foobar']))

    @pytest.mark.usefixtures('remove_dataset_groups')
    def test_tkeyword_to_value_group(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        grp = factories.Group(name='mygroup')

        config = {
            "dynamic_mapping": [
                {
                    "filters": [
                        "resource_type=='map'",
                        "tkeywords[?name=='nz' && thesaurus.uri == 'http://inspire.ec.europa.eu/theme']"
                    ],
                    "actions": [
                        {
                            "value": "mygroup",
                            "destination": "group"
                        }
                    ]
                }
            ]
        }

        pkg_dict = {
            'tags': [],
            'groups': []
        }
        extras = {}

        validate_config(config)
        parse_dynamic(config, geonode_map, pkg_dict, extras)

        self.assertIn('groups', pkg_dict)
        self.assertEqual(1, len(pkg_dict['groups']))
        self.assertEqual('mygroup', pkg_dict['groups'][0]['name'])


def load_test_file(filename):
    file = os.path.join(os.path.dirname(__file__), 'files', filename)
    with open(file, 'r') as f:
        return f.read()
