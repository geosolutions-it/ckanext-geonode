import json

from ckanext.geonode.harvesters.utils import format_date
from ckanext.geonode.model.types import GeoResource

THEME_BASE_URI = 'http://publications.europa.eu/resource/authority/data-theme/'
LANG_BASE_URI = 'http://publications.europa.eu/resource/authority/language/'
FREQ_BASE_URI = 'http://publications.europa.eu/resource/authority/frequency/'

OP_DATPRO = 'OP_DATPRO'

GEONODE_TO_SKOS_FREQ = {
    None: OP_DATPRO,
    'unknown': 'UNKNOWN',
    'continual': 'UPDATE_CONT',
    'notPlanned': 'NEVER',
    'asNeeded': 'OTHER',
    'irregular': 'IRREG',
    'daily': 'DAILY',
    'annually': 'ANNUAL',
    'monthly': 'MONTHLY',
    'fortnightly': 'WEEKLY_2',
    'weekly': 'WEEKLY',
    'biannually': 'ANNUAL_2',
    'quarterly': 'ANNUAL_3',
}

GEONODE_TO_SKOS_LANG = {
    'ita': 'ITA',
    'eng': 'ENG',
    'ger': 'DEU',
    'fra': 'FRA',
}

INSPIRE_TO_EUROVOC = {
    'ad': ['REGI',],
    'au': ['REGI',],
    'rs': ['ENVI','TECH'],
    'gg': ['ENVI','TECH'],
    'cp': ['REGI',],
    'gn': ['REGI',],
    'hy': ['ENVI',],
    'ps': ['ENVI',],
    'tn': ['TRAN',],
    'el': ['ENVI','TECH'],
    'ge': ['ENVI','TECH'],
    'lc': ['ENVI','AGRI'],
    'oi': ['ENVI','TECH'],
    'af': ['AGRI',],
    'am': ['GOVE','INTR'],
    'ac': ['ENVI',],
    'br': ['ENVI',],
    'bu': ['REGI',],
    'er': ['ENER',],
    'ef': ['ENVI','TECH'],
    'hb': ['ENVI',],
    'hh': ['SOCI','HEAL'],
    'lu': ['ENVI','AGRI'],
    'mr': ['ENVI',],
    'nz': ['ENVI','HEAL'],
    'of': ['ENVI','TECH'],
    'pd': ['SOCI',],
    'pf': ['ECON','TECH'],
    'sr': ['ENVI',],
    'so': ['ENVI',],
    'sd': ['ENVI','AGRI'],
    'su': ['GOVE','SOCI'],
    'us': ['GOVE','SOCI','HEAL'],
    'mf': ['ENVI','TECH'],
}


def parse_dcatapit_info(georesource: GeoResource, package_dict: dict, extras:dict ) -> (dict, dict):
    # dcatapit defines these fields:
        # identifier [1]                      OK
        # alternate_identifier [0..N]         OK (doi)
        # themes_aggregate [1..N]             OK (to be fixed))
        # publisher_name
        # publisher_identifier
        # issued  (release date) [0..1]       OK
        # modified ('Modification Date'), [1] OK
        # geographical_name
        # geographical_geonames_url
        # language [0..N]                     OK
        # temporal_coverage [0..N]            OK
        # - temporal_start                    OK
        # - temporal_end                      OK
        # holder_name
        # holder_identifier
        # frequency [1]                       OK
        # is_version_of
        # conforms_to
        # creator_name
        # creator_identifier

    # ### identifier [1]
    extras['identifier'] = georesource.get('uuid')

    # ### alternate_identifier [0..N]
    doi = georesource.get('doi')
    if doi:
        extras['alternate_identifier'] = json.dumps([{'identifier': doi}])

    # ### themes_aggregate [1..N]
    themes = []
    for tk in georesource.get('tkeywords', []):
        if tk['thesaurus']['uri'] == "http://inspire.ec.europa.eu/theme":
            name = tk['name']
            themes.extend(INSPIRE_TO_EUROVOC.get(name, []))
            if 'i18n' in tk and 'it' in tk['i18n']:
                package_dict['tags'].append({'name': tk['i18n']['it']})

    aggr = [{'theme': t, 'subthemes': []} for t in set(themes)]
    extras['themes_aggregate'] = json.dumps(aggr)

    # geonode "created": "2022-01-14T09:16:58.850532Z",
    # geonode "last_updated": "2022-01-14T09:16:59.993468Z",
    # "date": "2022-01-14T09:16:58.789761Z",
    # "date_type": "publication",
    if georesource.date_type() == 'publication':
        extras['issued'] = format_date(georesource.date())

    extras['modified'] = format_date(georesource.get('last_updated'))

    # ### geographical_name
    # geographical_geonames_url
    regions_names = [r['name'] for r in georesource.get('regions')]
    regions_codes = [r['code'] for r in georesource.get('regions')]

    # adding the region names as tags
    package_dict['tags'].extend([{'name': n} for n in regions_names])
    # Regions can be customised in GeoNode, so we need to put in proper codes from the regions
    if regions_codes:
        extras['geographical_name'] = '{' + ','.join(regions_codes) + '}'

    # ### language [0..N]
    # mapped in base mapper
    # GeoNode defines languages here: https://github.com/GeoNode/geonode/blob/3.3.x/geonode/base/enumerations.py#:~:text=ert/iso639.htm-,ALL_LANGUAGES,-%3D%20(
    extras['language'] = GEONODE_TO_SKOS_LANG.get(georesource.get('language'), OP_DATPRO)

    # ### temporal
    # geonode: "temporal_extent_start", "temporal_extent_end": null,
    # dcatapit: 'temporal_coverage': list of {'temporal_start': start, 'temporal_end': end}
    temporal_start = georesource.get('temporal_extent_start')
    temporal_end = georesource.get('temporal_extent_end')
    if temporal_start or temporal_end:
        interval = {
            'temporal_start': format_date(temporal_start) if temporal_start else None,
            'temporal_end': format_date(temporal_end) if temporal_end else None,
        }
        extras['temporal_coverage'] = json.dumps([interval])

    # ### frequency [1]
    freq = georesource.get('maintenance_frequency')
    extras['frequency'] = GEONODE_TO_SKOS_FREQ.get(freq, OP_DATPRO)

    return package_dict, extras

