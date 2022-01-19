import logging

from ckan import model
from ckan.logic import get_action, NotFound
from ckan.model import Session


ALLOWED_FIELDS = {
    'tkeywords': ('name', 'slug', 'uri', 'thesaurus__name', 'thesaurus__slug', 'thesaurus__uri',),
    'group': ('pk', 'name',)
}

log = logging.getLogger(__name__)


def validate_config(config):
    mapping = config.get('dynamic_mapping', {})
    for fieldname in mapping:
        if fieldname not in ('tkeywords', 'group', ):
            raise ValueError(f'Bad dynamic field "{fieldname}"')
        rules = mapping[fieldname]
        if not isinstance(rules, list):
            raise ValueError(f'Rules should be in a list')
        for rule in rules:
            if not isinstance(rule, dict):
                raise ValueError(f'Rule should be a dict')
            for rule_entry in rule:
                if rule_entry not in ('filters', 'actions', ):
                    raise ValueError(f'Rule can only have "filters" and "actions". Unknown entry "{rule_entry}"')
                if rule_entry == 'filters':
                    filters = rule[rule_entry]
                    if not isinstance(filters, list):
                        raise ValueError(f'Filters should be a list')
                    for filter in filters:
                        if not isinstance(filter, dict):
                            raise ValueError(f'Filter in "{fieldname}" should be a list')
                        for filter_field in filter:
                            if filter_field not in ('field', 'value',):
                                raise ValueError(f'Unknown filter field "{filter_field}"')
                        for name in ('field', 'value',):
                            if name not in filter:
                                raise ValueError(f'Missing filter field "{name}"')
                        if filter['field'] not in ALLOWED_FIELDS[fieldname]:
                            raise ValueError(f'Unknown filter field "{filter["field"]}" for dynamic field "{fieldname}"')
                elif rule_entry == 'actions':
                    actions = rule[rule_entry]
                    if not isinstance(actions, list):
                        raise ValueError(f'Actions should be a list')
                    for action in actions:
                        for action_field in action:
                            if action_field not in ('destination', 'value', 'field'):
                                raise ValueError(f'Unknown action field "{action_field}"')
                        if 'destination' not in action:
                            raise ValueError(f'Missing action field "destination"')
                        if not any(s in action for s in ('field', 'value',)):
                            raise ValueError(f'At least one in "field","value" is required in Action')

                        if 'field' in action:
                            if action['field'] not in ALLOWED_FIELDS[fieldname]:
                                raise ValueError(f'Bad action value field "{action["value"]}" for dynamic field "{fieldname}"')
                        if not isinstance(action['destination'], str):
                            raise ValueError(f'Action destination should be a string')


def parse_georesource(config, georesource, package_dict, extras):
    mapping = config.get('dynamic_mapping', {})
    if 'tkeywords' in mapping:
        parse_tkeywords(mapping['tkeywords'], georesource.get('tkeywords'), package_dict, extras)
    if 'group' in mapping:
        parse_group(mapping['group'], georesource.get('group'), package_dict, extras)

    return package_dict, extras


def _get_field(field_name, obj, allowed_fields):
    if field_name not in allowed_fields:
        raise ValueError(f'Field not allowed "{field_name}"')
    if '__' not in field_name:
        return obj[field_name]

    sub_field = field_name.split('__')[0]
    field_name = field_name.split('__')[-1]

    sub_obj = obj[sub_field]
    return sub_obj[field_name]


def _check_filters(filters, obj, allowed_fields):
    for filter in filters:
        value = _get_field(filter['field'], obj, allowed_fields)
        if value != filter['value']:
            return False
    return True


def _apply_actions(actions, obj, package_dict, extras, allowed_fields):
    for action in actions:
        if 'field' in action:
            value = _get_field(action['field'], obj, allowed_fields)
        elif 'value' in action:
            value = action['value']
        else:
            raise ValueError(f'Missing source info for action {action}')
        dst = action['destination']
        set_value(value, dst, package_dict, extras)


def set_value(value, dst, package_dict, extras):
    if dst == 'tag':
        package_dict['tags'].append({'name': value})
    elif dst == 'group':
        if _validate_group(value):
            package_dict['groups'].append({'name': value})
    else:
        if dst not in extras:
            extras[dst] = value
        else:
            old = extras[dst]
            if isinstance(old, list):
                extras[dst].append(value)
            else:
                extras[dst] = [old, value]

def _validate_group(group):
    try:
        context = {'model': model, 'session': Session, 'user': 'harvest'}
        data_dict = {'id': group}
        get_action('group_show')(context, data_dict)
        return True
    except NotFound:
        log.warning(f'Group {group} is not available')
        return False


def _apply_rules(rules, obj, package_dict, extras, allowed_fields):
    if not obj:
        log.debug("skipping null object")
        return
    for rule in rules:
        if _check_filters(rule['filters'], obj, allowed_fields):
            log.debug(f'Filters ok for rule {rule} obj {obj}')
            _apply_actions(rule['actions'], obj, package_dict, extras, allowed_fields)


def parse_tkeywords(rules, tkeywords, package_dict, extras):
    for tkeyword in tkeywords:
        log.debug(f'Checking mapping for tk {tkeyword["name"]}')
        _apply_rules(rules, tkeyword, package_dict, extras, ALLOWED_FIELDS['tkeywords'])


def parse_group(rules, group, package_dict, extras):
    _apply_rules(rules, group, package_dict, extras, ALLOWED_FIELDS['group'])
