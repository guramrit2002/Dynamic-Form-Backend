def evaluate_condition(condition, data):
    """Returns True if the condition is satisfied by data."""
    if not condition:
        return True

    field = condition.get('field')
    operator = condition.get('operator')
    expected = condition.get('value')
    actual = data.get(field)

    if actual is None:
        return False

    try:
        if operator == '==':
            return str(actual) == str(expected)
        if operator == '!=':
            return str(actual) != str(expected)
        if operator == '>':
            return float(actual) > float(expected)
        if operator == '<':
            return float(actual) < float(expected)
        if operator == '>=':
            return float(actual) >= float(expected)
        if operator == '<=':
            return float(actual) <= float(expected)
    except (ValueError, TypeError):
        pass

    return False


def get_visible_fields(schema, data):
    """Returns a set of field ids that are visible given the current data."""
    visible = set()
    for step in schema.get('steps', []):
        for field in step.get('fields', []):
            visibility = field.get('visibility')
            if visibility:
                if evaluate_condition(visibility.get('condition'), data):
                    visible.add(field['id'])
            else:
                visible.add(field['id'])
    return visible
