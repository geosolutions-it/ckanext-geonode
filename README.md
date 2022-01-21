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

1. Install the ckanext-geonode requirements into your virtual environment:
   ```bash
   cd ckanext-geonode
   (venv) $ pip install -r requirements.txt
   ```

1. Install the ckanext-geonode Python package into your virtual environment:
   ```bash
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
- `dynamic_mapping`: add values to local dataset according to values in the GeoNode resource; you can add `tag`s, `extra`s, or associate the dataset to groups.  
   See next section for configurating a dynamic mapping.


### Dynamic mapping

Mapping is defined through a list of Rules:
```json
{
   "dynamic_mapping": [
      RULE,
      ...
    ]
}
```
For each harvested object, all the Rules are checked.

Each **Rule** is composed by a list of Filters (possibily empty) and a list of Actions.  

```json
{
    "filters": [
        FILTER,
        ...
    ],
    "actions": [
        ACTION,
        ...
    ]
}
```
If the checks on all of the filters are satisfied, the Actions are applied.


A **Filter** is a string representing a [JMESPath](https://jmespath.org/).  
It is evaluated as True if it returns a value or a non empty list.
e.g.
```
"tkeywords[?name=='nz' && thesaurus.uri == 'http://inspire.ec.europa.eu/theme']"
```
If all Filters in a Rule are passing, the related **Action**s are then applied.

An **Action** tells how values are to be stored in the CKAN package.  
The Action is a dict with the following content:
- `destination`: (required), may be:
  - `tag`: the selected value(s) are stored as tags
  - `group`: the selected value(s) are used to link groups to the dataset
  - any other string is used as the name of the extra field that will be created or extended with the new values.
- `value`: (mutex with `source`) a fixed string that will be used/stored in the `destination`
- `source`: (mutex with value) a JMESPath used to extract values from the GeoNode resource.  
   It may return a string or a list of strings.  
   If nothing is extracted, the action will be skipped.
- `mapping`: (optional, can only be used when `source` is defined). A mapping from the values extracted by the `source` to the values that shall be stored.  
   If the extracted value is not mapped to anything, the action will be skipped.


Examples:
1. If there is at least a keyword from the INSPIRE theme thesaurus, add the "INSPIRE" tag:
   ```json
   { "dynamic_mapping": [
        {"filters": ["tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme']"],
         "actions": [
                { "destination": "tag",
                  "value": "INSPIRE"}
            ]
        }
     ]
   }
   ```

1. Add as tags the short name of the INPIRE themes:
   ```json
   { "dynamic_mapping": [
       { "filters": [],
         "actions": [
            { "source": "tkeywords[?thesaurus.uri == 'http://inspire.ec.europa.eu/theme'].name",
              "destination": "tag"
            }
        ]
       }
     ]
   }
   ```
1. If it's a map and it's about natural risk zones, bind it to to group "mygroup":
   ```json
   { "dynamic_mapping": [
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
   ```

1. Map some GeoNode groups into CKAN groups:
   ```json
   { "dynamic_mapping": [
        {
           "filters": [],
           "actions": [
              {              
                 "source": "group.name",
                 "mapping": {
                    "GN1": "ckan1",
                    "GN2": "ckan2"
                 },
                 "destination": "group"
              }
           ]
        }
     ]
   }
   ```
      
