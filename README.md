# `ckanext-geonode`:  a GeoNode harvester for CKAN

This extensions implements a GeoNode harvester using GeoNode's own API.

Even if GeoNode layers may be queried using CSW, you can't get maps or documents as CSW records.  
Furthermore, by using the internal API for layers also, we can retrieve some more information that
are not published along with the CSW metadata.

## Compatibility

This extension has been tested using python 3.7 and CKAN2.9.

For previous versions of CKAN please use the tag [`pre-py3`](https://github.com/geosolutions-it/ckanext-geonode/tree/pre-py3)

# Installation

1. Clone the project:
   ```bash
   git clone https://github.com/https://github.com/geosolutions-it/ckanext-geonode.git

1. Activate your CKAN virtual environment, for example:
   ```bash
   . /usr/lib/ckan/default/bin/activate
   ```

1. Install the ckanext-geonode Python package into your virtual environment:
   ```bash
   cd ckanext-geonode
   (venv) $ pip install -e .
   ```

# Configuration

1. Make sure the CKAN configuration ini file contains the `geonode_harvester` plugin, as
   well as the `harvest` plugin (provided in the [`ckanext-harvest` plugin](https://github.com/ckan/ckanext-harvest))::
   ```ini
   ckan.plugins = [...] harvest [...] geonode_harvester
   ``` 

# Harvester configuration

When creating/editing a geonode harvester instance, you may use these configuration items:
 
- `import`: used to harvest only some resources subtypes (`layers`, `maps`, `docs`).   
  By default the harvester will read all subtypes; If the `import` configuration is given,
  only the selected entries will be harvested.  
  e.g.  
  ```json
  {"import": {"maps": true}}
  ```
- `import_fields`: a list of field names to be imported from the remote JSON into the local dataset.

## Group mapping

You may associate groups to the harvested dataset according to fields in the GeoNode resource JSON.  
You need to define these keys on the harvester configuration:
- `group_mapping_fieldname`: the name of the field in the GeoNode resource JSON to use as a key 
  for the group mapping
- `group_mapping`: a dict containing the mapping from the remote value to the local group name.  
   The remote value is the value extracted from the resource JSON in the field 
   indicated by `group_mapping_fieldname`

