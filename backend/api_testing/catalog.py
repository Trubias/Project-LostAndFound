import re

from django.urls import URLPattern, URLResolver, get_resolver


CONTROL_PREFIX = 'api/test-console/'
HTTP_METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')
REQUEST_PARAMETERS = {
    'api/items/': {
        'query': ['q', 'type', 'category', 'page'],
        'body': [],
    },
    'items/api/': {
        'query': ['q', 'type', 'category', 'page'],
        'body': [],
    },
    'api/frontend-page/': {
        'query': ['path', 'q', 'type', 'role', 'status', 'category', 'handoff', 'page', 'reported'],
        'body': [],
    },
    'api/admin/<path:action>/': {
        'query': [],
        'body': ['role', 'reviewer_notes', 'name', 'description', 'kind', 'active'],
    },
    'api/match-suggestions/': {
        'query': [],
        'body': ['item_type', 'category', 'title', 'description', 'location', 'building', 'room', 'workstation', 'date_occurred', 'image'],
    },
}


def _walk(patterns, prefix=''):
    for entry in patterns:
        route = f'{prefix}{entry.pattern}'
        if isinstance(entry, URLResolver):
            yield from _walk(entry.url_patterns, route)
        elif isinstance(entry, URLPattern):
            yield route, entry


def _sample_path(route):
    parameters = []

    def replace(match):
        converter = match.group('converter') or 'str'
        name = match.group('name')
        parameters.append(name)
        samples = {
            'int': '1',
            'str': 'test-value',
            'slug': 'test-value',
            'uuid': '00000000-0000-0000-0000-000000000001',
            'path': 'test-action',
        }
        return samples.get(converter, 'test-value')

    path = re.sub(r'<(?:(?P<converter>[^:<>]+):)?(?P<name>[^<>]+)>', replace, route)
    return '/' + path.lstrip('/'), parameters


def discover_api_endpoints():
    endpoints = []
    for route, entry in _walk(get_resolver().url_patterns):
        route = str(route).lstrip('/')
        if not re.search(r'(^|/)api(/|$)', route) or route.startswith(CONTROL_PREFIX):
            continue
        path, parameters = _sample_path(route)
        declared_parameters = REQUEST_PARAMETERS.get(route, {'query': [], 'body': []})
        endpoints.append({
            'id': route,
            'name': entry.name or route,
            'pattern': '/' + route,
            'sample_path': path,
            'path_parameters': parameters,
            'query_parameters': declared_parameters['query'],
            'body_parameters': declared_parameters['body'],
            'methods': list(HTTP_METHODS),
        })
    return sorted(endpoints, key=lambda endpoint: endpoint['pattern'])
