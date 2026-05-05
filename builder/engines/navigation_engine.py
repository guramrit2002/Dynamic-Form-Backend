from .condition_engine import evaluate_condition


def get_next_step(schema, current_step_id, data):
    """
    Returns the next step id based on navigation rules, or None if the form is complete.
    Checks explicit navigation rules first, then falls back to linear order.
    """
    navigation = schema.get('navigation', [])

    for nav in navigation:
        if nav.get('from_step') != current_step_id:
            continue
        condition = nav.get('condition')
        if condition is None or evaluate_condition(condition, data):
            return nav.get('to_step')

    step_ids = [s['id'] for s in schema.get('steps', [])]
    if current_step_id in step_ids:
        idx = step_ids.index(current_step_id)
        if idx + 1 < len(step_ids):
            return step_ids[idx + 1]

    return None


def get_step_by_id(schema, step_id):
    for step in schema.get('steps', []):
        if step['id'] == step_id:
            return step
    return None
