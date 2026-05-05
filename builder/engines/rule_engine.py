from .condition_engine import evaluate_condition


def execute_rules(schema, data):
    """
    Executes post-submission rules against the data.
    Returns a new dict with any rule-driven mutations applied.
    """
    result = dict(data)

    for rule in schema.get('rules', []):
        if evaluate_condition(rule.get('if'), result):
            _apply_action(rule.get('then', {}), result)

    return result


def _apply_action(action, data):
    action_type = action.get('action')

    if action_type == 'set_value':
        field = action.get('field')
        if field:
            data[field] = action.get('value')

    elif action_type == 'tag':
        tags = data.setdefault('_tags', [])
        tag = action.get('value')
        if tag and tag not in tags:
            tags.append(tag)

    elif action_type == 'set_status':
        data['_status'] = action.get('value')
