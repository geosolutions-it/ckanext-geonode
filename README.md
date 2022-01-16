# GeoNode harvester for CKAN

# Description

Harvests GeoNode instances using GeoNode's own API.

Even if GeoNode may be queried using CSW, there are some issues in parsing the ISO19139 document,
such as detecting the resource type (some versions do not differentiate between
maps and layers).

Furthermore, by using the internal API, we can retrieve some more information, such as the DOI.

# Configuration

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
