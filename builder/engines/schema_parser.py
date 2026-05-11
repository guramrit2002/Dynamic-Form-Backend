FIELD_TYPES = {'text', 'textarea', 'number', 'email', 'date', 'select', 'checkbox', 'radio'}
OPERATORS = {'==', '!=', '>', '<', '>=', '<='}
VALIDATION_TYPES = {'min', 'max', 'regex'}
RULE_ACTIONS = {'set_value', 'tag', 'set_status'}


def parse_and_validate(schema):
    """Returns (is_valid: bool, errors: list)."""
    if not isinstance(schema, dict):
        return False, ['Schema must be a JSON object.']

    errors = []

    if 'steps' not in schema:
        return False, ['Schema must have a "steps" key.']

    if not isinstance(schema['steps'], list) or len(schema['steps']) == 0:
        errors.append('"steps" must be a non-empty list.')
    else:
        field_ids = set()
        for i, step in enumerate(schema['steps']):
            errors.extend(_validate_step(step, i, field_ids))

    if 'navigation' in schema:
        if not isinstance(schema['navigation'], list):
            errors.append('"navigation" must be a list.')
        else:
            for i, nav in enumerate(schema['navigation']):
                errors.extend(_validate_navigation(nav, i))

    if 'rules' in schema:
        if not isinstance(schema['rules'], list):
            errors.append('"rules" must be a list.')
        else:
            for i, rule in enumerate(schema['rules']):
                errors.extend(_validate_rule(rule, i))

    return len(errors) == 0, errors


def _validate_step(step, index, field_ids):
    errors = []
    prefix = f'steps[{index}]'

    if not isinstance(step, dict):
        return [f'{prefix}: must be an object.']

    for key in ('id', 'title'):
        if key not in step:
            errors.append(f'{prefix}: missing "{key}".')

    if 'fields' not in step:
        errors.append(f'{prefix}: missing "fields".')
    elif not isinstance(step['fields'], list):
        errors.append(f'{prefix}.fields: must be a list.')
    else:
        for j, field in enumerate(step['fields']):
            errors.extend(_validate_field(field, index, j, field_ids))

    return errors


def _validate_field(field, step_index, field_index, field_ids):
    errors = []
    prefix = f'steps[{step_index}].fields[{field_index}]'

    if not isinstance(field, dict):
        return [f'{prefix}: must be an object.']

    if 'id' not in field:
        errors.append(f'{prefix}: missing "id".')
    elif field['id'] in field_ids:
        errors.append(f'{prefix}: duplicate field id "{field["id"]}".')
    else:
        field_ids.add(field['id'])

    if 'type' not in field:
        errors.append(f'{prefix}: missing "type".')
    elif field['type'] not in FIELD_TYPES:
        errors.append(f'{prefix}: invalid type "{field["type"]}". Must be one of {sorted(FIELD_TYPES)}.')

    if 'label' not in field:
        errors.append(f'{prefix}: missing "label".')

    if 'validations' in field:
        if not isinstance(field['validations'], list):
            errors.append(f'{prefix}.validations: must be a list.')
        else:
            for k, rule in enumerate(field['validations']):
                errors.extend(_validate_validation_rule(rule, prefix, k))

    if 'visibility' in field and isinstance(field['visibility'], dict):
        errors.extend(_validate_condition(field['visibility'].get('condition'), f'{prefix}.visibility'))

    return errors


def _validate_validation_rule(rule, prefix, index):
    errors = []
    r_prefix = f'{prefix}.validations[{index}]'

    if not isinstance(rule, dict):
        return [f'{r_prefix}: must be an object.']

    if 'type' not in rule:
        errors.append(f'{r_prefix}: missing "type".')
    elif rule['type'] not in VALIDATION_TYPES:
        errors.append(f'{r_prefix}: invalid type "{rule["type"]}". Must be one of {sorted(VALIDATION_TYPES)}.')

    if 'value' not in rule:
        errors.append(f'{r_prefix}: missing "value".')

    return errors


def _validate_condition(condition, prefix):
    if condition is None:
        return [f'{prefix}: missing "condition".']

    if not isinstance(condition, dict):
        return [f'{prefix}.condition: must be an object.']

    errors = []
    for key in ('field', 'operator', 'value'):
        if key not in condition:
            errors.append(f'{prefix}.condition: missing "{key}".')

    if 'operator' in condition and condition['operator'] not in OPERATORS:
        errors.append(f'{prefix}.condition: invalid operator "{condition["operator"]}". Must be one of {sorted(OPERATORS)}.')

    return errors


def _validate_navigation(nav, index):
    errors = []
    prefix = f'navigation[{index}]'

    if not isinstance(nav, dict):
        return [f'{prefix}: must be an object.']

    for key in ('from_step', 'to_step'):
        if key not in nav:
            errors.append(f'{prefix}: missing "{key}".')

    if 'condition' in nav:
        errors.extend(_validate_condition(nav['condition'], prefix))

    return errors


def _validate_rule(rule, index):
    errors = []
    prefix = f'rules[{index}]'

    if not isinstance(rule, dict):
        return [f'{prefix}: must be an object.']

    if 'if' not in rule:
        errors.append(f'{prefix}: missing "if".')
    else:
        errors.extend(_validate_condition(rule['if'], f'{prefix}.if'))

    if 'then' not in rule:
        errors.append(f'{prefix}: missing "then".')
    else:
        then = rule['then']
        if not isinstance(then, dict):
            errors.append(f'{prefix}.then: must be an object.')
        else:
            if 'action' not in then:
                errors.append(f'{prefix}.then: missing "action".')
            elif then['action'] not in RULE_ACTIONS:
                errors.append(f'{prefix}.then: invalid action "{then["action"]}". Must be one of {sorted(RULE_ACTIONS)}.')

    return errors