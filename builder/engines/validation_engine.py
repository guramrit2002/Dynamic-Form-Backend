import re
from .condition_engine import get_visible_fields


def validate_submission(schema, data):
    """
    Validates submission data against the form schema.
    Returns (is_valid: bool, errors: dict keyed by field id).
    Only validates fields that are currently visible.
    """
    errors = {}
    visible_fields = get_visible_fields(schema, data)

    all_fields = {}
    for step in schema.get('steps', []):
        for field in step.get('fields', []):
            all_fields[field['id']] = field

    for field_id, field in all_fields.items():
        if field_id not in visible_fields:
            continue
        field_errors = _validate_field(field, data.get(field_id))
        if field_errors:
            errors[field_id] = field_errors

    return len(errors) == 0, errors


def _validate_field(field, value):
    errors = []
    is_empty = value is None or value == '' or value == []

    if field.get('required') and is_empty:
        return ['This field is required.']

    if is_empty:
        return []

    for rule in field.get('validations', []):
        error = _apply_rule(rule.get('type'), rule.get('value'), value)
        if error:
            errors.append(error)

    return errors


def _apply_rule(rule_type, rule_value, value):
    if rule_type == 'min':
        try:
            if float(value) < float(rule_value):
                return f'Value must be at least {rule_value}.'
        except (ValueError, TypeError):
            if len(str(value)) < int(rule_value):
                return f'Minimum length is {rule_value}.'

    elif rule_type == 'max':
        try:
            if float(value) > float(rule_value):
                return f'Value must be at most {rule_value}.'
        except (ValueError, TypeError):
            if len(str(value)) > int(rule_value):
                return f'Maximum length is {rule_value}.'

    elif rule_type == 'regex':
        if not re.fullmatch(str(rule_value), str(value)):
            return 'Value does not match the required pattern.'

    return None
