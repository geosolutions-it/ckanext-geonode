import json
import os
import pytest
import unittest

from ckan.model.meta import Session

from ckan.tests import helpers, factories

from ckanext.geonode.harvesters.mappers.dynamic import parse_georesource, validate_config


class DynamicMapperTestCase(unittest.TestCase):

    def setUp(self):
        pass

    def test_tk_thes_and_name_to_value_tag(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping':
                {
                    'tkeywords': [
                        {
                            'filters': [
                                {
                                    'field': 'thesaurus__uri',
                                    'value': 'http://inspire.ec.europa.eu/theme'
                                },
                                {
                                    'field': 'name',
                                    'value': 'nz'
                                }
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
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_georesource(config, geonode_map, pkg_dict, extras)

        tags = pkg_dict['tags']
        self.assertEqual(1, len(tags))
        self.assertEqual('Rischio naturale', tags[0]['name'])


    def test_tk_multiple_thes_to_field_tag(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping':
                {
                    'tkeywords': [
                        {
                            'filters': [
                                {
                                    'field': 'thesaurus__uri',
                                    'value': 'http://inspire.ec.europa.eu/theme'
                                },
                                ],
                           'actions': [
                               {
                                   'field': 'name',
                                   'destination': 'tag'
                               }
                            ]
                        }
                    ]
                }
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_georesource(config, geonode_map, pkg_dict, extras)

        tags = pkg_dict['tags']
        self.assertEqual(2, len(tags))
        tags_content = set([tag['name'] for tag in tags])
        self.assertSetEqual(set(('nz', 'hb')), tags_content)


    def test_tk_multiple_thes_to_extras(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        config = {
            'dynamic_mapping':
                {
                    'tkeywords': [
                        {
                            'filters': [
                                {
                                    'field': 'thesaurus__uri',
                                    'value': 'http://inspire.ec.europa.eu/theme'
                                },
                                ],
                           'actions': [
                               {
                                   'field': 'name',
                                   'destination': 'foobar'
                               }
                            ]
                        }
                    ]
                }
        }

        pkg_dict = {
            'tags': []
        }
        extras = {}

        validate_config(config)
        package_dict, extras = parse_georesource(config, geonode_map, pkg_dict, extras)

        self.assertEqual(1, len(extras))
        self.assertTrue(isinstance(extras['foobar'], list))
        self.assertEqual(2, len(extras['foobar']))
        self.assertSetEqual(set(('nz', 'hb')), set(extras['foobar']))

    @pytest.mark.usefixtures('remove_dataset_groups')
    def test_tk_thes_and_name_to_group(self):
        geonode_map = json.loads(load_test_file('map01.json'))

        grp = factories.Group(name='mygroup')

        config = {
            'dynamic_mapping':
                {
                    'tkeywords': [
                        {
                            'filters': [
                                {
                                    'field': 'thesaurus__uri',
                                    'value': 'http://inspire.ec.europa.eu/theme'
                                },
                                {
                                    'field': 'name',
                                    'value': 'nz'
                                }
                                ],
                           'actions': [
                               {
                                   'value': 'mygroup',
                                   'destination': 'group'
                               }
                            ]
                        }
                    ]
                }
        }

        pkg_dict = {
            'tags': [],
            'groups': []
        }
        extras = {}

        validate_config(config)
        parse_georesource(config, geonode_map, pkg_dict, extras)

        self.assertIn('groups', pkg_dict)
        self.assertEqual(1, len(pkg_dict['groups']))
        self.assertEqual('mygroup', pkg_dict['groups'][0]['name'])


def load_test_file(filename):
    file = os.path.join(os.path.dirname(__file__), 'files', filename)
    with open(file, 'r') as f:
        return f.read()

        config = {
            "dynamic_mapping":
                {
                    "group": [
                        {
                            "filters": [
                                {
                                    "field": "name",
                                    "value": "ATL"
                                },
                                ],
                           "actions": [
                               {
                                   "value": "atlante-cartografico",
                                   "destination": "group"
                               }
                            ]
                        }
                    ]
                }
        }
