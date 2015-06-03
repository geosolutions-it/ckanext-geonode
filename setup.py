from setuptools import setup, find_packages
import sys, os

version = '1.1'

setup(
    name='ckanext-geonode',
    version=version,
    description="CKAN harvester for GeoNode",
    long_description="""\
    """,
    classifiers=[],  # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
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
        # Add plugins here, eg
        # myplugin=ckanext.geonode:PluginClass
        geonode_harvester=ckanext.geonode.harvesters:GeoNodeHarvester
            """,
)
