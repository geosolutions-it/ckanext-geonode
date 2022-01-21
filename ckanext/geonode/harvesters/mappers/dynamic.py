import logging

import jmespath
from jmespath import parser
from jmespath.exceptions import ParseError

from ckan import model
from ckan.logic import get_action, NotFound
from ckan.model import Session


log = logging.getLogger(__name__)
p = parser.Parser()


def validate_config(config):
    rules = config.get('dynamic_mapping', [])
    if not isinstance(rules, list):
        raise ValueError(f'dynamic_mapping should be a list of Rules')
    for rule_idx, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise ValueError(f'Rule #{rule_idx}: Rule should be a dict')
        if set(rule.keys()) != set(('filters', 'actions')):
            raise ValueError(f'Rule #{rule_idx}: Rule must have "filters" and "actions" keys, found {rule.keys()}')

        filters = rule['filters']
        if not isinstance(filters, list):
            raise ValueError(f'Rule #{rule_idx}: Filters should be a list')
        for filter in filters:
            if not isinstance(filter, str):
                raise ValueError(f'Rule #{rule_idx}: Filter should be a str')
            try:
                p.parse(filter)
            except ParseError as e:
                raise ValueError(f'Rule #{rule_idx}: Filter not parsable FILTER:[{filter}] ERR:[{str(e)}]')

        actions = rule['actions']
        if not isinstance(actions, list):
            raise ValueError(f'Rule #{rule_idx}: Actions should be a list')
        for action in actions:
            if not isinstance(action, dict):
                raise ValueError(f'Rule #{rule_idx}: Action should be a dict')
            for action_key in action:
                if action_key not in ('destination', 'value', 'source', 'mapping'):
                    raise ValueError(f'Rule #{rule_idx}: Unknown Action key "{action_key}"')
            if 'destination' not in action:
                raise ValueError(f'Rule #{rule_idx}: Missing action field "destination"')
            elif not isinstance(action['destination'], str):
                raise ValueError(f'Rule #{rule_idx}: Action "destination" should be a string')

            if not any(s in action for s in ('source', 'value',)):
                raise ValueError(f'Rule #{rule_idx}: At least one in "source","value" is required in Action')

            if 'mapping' in action:
                if 'source' not in action:
                    raise ValueError(f'Rule #{rule_idx}: "mapping" is only possible when "source" is defined in Action')
                if not isinstance(action['mapping'], dict):
                    raise ValueError(f'Rule #{rule_idx}: "mapping" should be a dict')

            if 'source' in action:
                try:
                    p.parse(action['source'])
                except ParseError as e:
                    raise ValueError(f'Rule #{rule_idx}: "source" not parsable SOURCE:[{action["source"]}] ERR:[{str(e)}]')


def parse_dynamic(config, obj, package_dict, extras):
    rules = config.get('dynamic_mapping', [])

    for rx, rule in enumerate(rules):
        if _evaluate_filters(rule['filters'], obj, rx):
            log.debug(f'Rule #{rx}: Filters passed for rule {rule}')
            _apply_actions(rule['actions'], obj, package_dict, extras, rx)

    return package_dict, extras


def _evaluate_filters(filters, obj, rx):
    # returns True if all filters are satisfied
    for filter in filters:
        if not jmespath.search(filter, obj):
            log.debug(f'Rule #{rx}: Filter failed: {filter}')
            return False

    return True


def _apply_actions(actions, obj, package_dict, extras, rx):
    for action in actions:
        if 'source' in action:
            value = jmespath.search(action['source'], obj)
            if not value:
                log.debug(f'Rule #{rx}: Source selected no data: {action["source"]}')
                continue
            if 'mapping' in action:
                mapped_value = _apply_mapping(action['mapping'], value, rx)
                if mapped_value is None or mapped_value == []:
                    log.debug(f'Rule #{rx}: Mapping produced no data for value "{value}"')
                    continue
                value = mapped_value
        elif 'value' in action:
            value = action['value']
        else:
            raise ValueError(f'Rule #{rx}: Missing source info for action {action}')  # should not happen
        dst = action['destination']
        set_value(value, dst, package_dict, extras, rx=rx)


def _apply_mapping(mapping: dict, value, rx: int):
    if isinstance(value, str):
        return _apply_single_mapping(mapping, value, rx)
    elif isinstance(value, list):
        ret = [_apply_single_mapping(mapping, v, rx) for v in value]
        return [x for x in ret if x is not None]
    else:
        log.error(f'Rule #{rx}: Skipping mapping of unknown type {type(value)}: {value}')
        return None


def _apply_single_mapping(mapping: dict, value, rx: int):
    if value in mapping:
        new_value = mapping[value]
        log.debug(f'Rule #{rx}: Mapping "{value}" to "{new_value}"')
        return new_value
    else:
        log.debug(f'Rule #{rx}: Skipping unmapped value "{value}"')
        return None


def set_value(value, dst, package_dict, extras, rx=-1):
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f'Rule #{rx}: Unexpected type {type(value)}: {value}')

    if dst == 'tag':
        log.debug(f'Rule #{rx}: adding tags {values} to package {package_dict.get("title", "")}')
        package_dict['tags'].extend([{'name': v} for v in values])
    elif dst == 'group':
        for g in values:
            if _validate_group(g):
                package_dict['groups'].append({'name': g})
    else:
        set_extra(dst, value, extras)


def set_extra(name, value, extras):
    if isinstance(value, list):
        if len(value) == 0:
            return
        elif len(value) == 1:
            value = value  # unwrap

    if name not in extras:
        extras[name] = value
    else:
        if isinstance(extras[name], list):
            if isinstance(value, list):
                extras[name].extend(value)
            if isinstance(value, str):
                extras[name].append(value)
        else:
            if isinstance(value, list):
                extras[name] = [extras[name]]
                extras[name].extend(value)
            if isinstance(value, str):
                extras[name] = [extras[name], value]

def _validate_group(group):
    try:
        context = {'model': model, 'session': Session, 'user': 'harvest'}
        data_dict = {'id': group}
        get_action('group_show')(context, data_dict)
        return True
    except NotFound:
        log.warning(f'Group {group} is not available')
        return False
