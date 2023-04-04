from setuptools import setup, find_packages
import sys, os

version = '1.3'

setup(
    name='ckanext-geonode',
    version=version,
    description="CKAN harvester for GeoNode",
    long_description="""\
    """,
    classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='CKAN GeoNode APIv2 harvest GeoSolutions',
    author='Emanuele Tajariol',
    author_email='etj@geo-solutions.it',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.geonode'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
       # -*- Extra requirements: -*-
    ],
    entry_points=
    """
        [ckan.plugins]
        geonode_harvester=ckanext.geonode.harvesters.geonode:GeoNodeHarvester
        geonode=ckanext.geonode.plugin:GeoNodePlugin
    """,

    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
