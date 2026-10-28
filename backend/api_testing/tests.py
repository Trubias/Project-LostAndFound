import json
import time
from unittest.mock import patch
from urllib.parse import urlencode

from django.apps import apps
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import Client, TestCase

from accounts.models import Profile
from items.models import Item
from .models import ApiTestRun

from .catalog import CONTROL_PREFIX, HTTP_METHODS, discover_api_endpoints


PROBE_FILTER = {'endpoint_id': '', 'method': ''}
PROBE_RESULTS = []


def configure_probe(endpoint_id='', method=''):
    PROBE_FILTER.update(endpoint_id=endpoint_id, method=method)
    PROBE_RESULTS.clear()


def _database_counts():
    counts = {}
    for model in apps.get_models():
        if model._meta.managed and not model._meta.proxy:
            counts[model._meta.label] = model._default_manager.count()
    return counts


def _request(client, method, path, query_parameters):
    if query_parameters:
        path = f'{path}?{urlencode(query_parameters)}'
    if method in ('GET', 'HEAD', 'OPTIONS', 'DELETE'):
        return client.generic(method, path)
    return client.generic(method, path, data=b'{}', content_type='application/json')


class APIEndpointMethodSmokeTests(TestCase):
    def test_discovered_api_routes_and_methods(self):
        endpoints = discover_api_endpoints()
        endpoints = [endpoint for endpoint in endpoints if not endpoint['id'].startswith(CONTROL_PREFIX)]
        if PROBE_FILTER['endpoint_id']:
            endpoints = [endpoint for endpoint in endpoints if endpoint['id'] == PROBE_FILTER['endpoint_id']]
            self.assertTrue(endpoints, f"Unknown API endpoint: {PROBE_FILTER['endpoint_id']}")

        probes = [
            (endpoint, method)
            for endpoint in endpoints
            for method in HTTP_METHODS
            if not PROBE_FILTER['method'] or method == PROBE_FILTER['method']
        ]
        self.assertTrue(probes, 'No API endpoint methods were selected.')

        client = Client()
        for endpoint, method in probes:
            sample_values = {
                'path': '/',
                'q': 'api-test',
                'type': 'FOUND',
                'category': '1',
                'page': '1',
                'role': 'USER',
                'status': 'active',
                'handoff': 'open',
                'reported': '1',
            }
            query_parameters = {
                name: sample_values[name]
                for name in endpoint['query_parameters']
                if name in sample_values
            }
            started = time.perf_counter()
            response = None
            database_changed = False
            error = ''
            try:
                with transaction.atomic():
                    before = _database_counts()
                    response = _request(client, method, endpoint['sample_path'], query_parameters)
                    after = _database_counts()
                    database_changed = before != after
                    transaction.set_rollback(True)
            except Exception as exc:
                error = f'{type(exc).__name__}: {exc}'
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            body = ''
            headers = {}
            status = None
            if response is not None:
                status = response.status_code
                body = response.content.decode(response.charset or 'utf-8', errors='replace')[:4000]
                headers = {
                    key: response.headers[key]
                    for key in ('Content-Type', 'Allow', 'Location')
                    if key in response.headers
                }
            passed = not error and status is not None and status < 500
            PROBE_RESULTS.append({
                'endpoint_id': endpoint['id'],
                'endpoint': endpoint['pattern'],
                'method': method,
                'request': {
                    'path': endpoint['sample_path'],
                    'path_parameters': endpoint['path_parameters'],
                    'query_parameters': query_parameters,
                    'payload': {} if method in ('POST', 'PUT', 'PATCH') else None,
                },
                'response': {
                    'status': status,
                    'headers': headers,
                    'body': body,
                },
                'duration_ms': elapsed_ms,
                'database_changed': database_changed,
                'status_result': 'passed' if passed else 'failed',
                'error': error,
            })
            self.assertTrue(passed, f'{method} {endpoint["sample_path"]} failed: {error or status}')


class APIEndpointCatalogTests(TestCase):
    def test_catalog_discovers_methods_and_known_request_parameters(self):
        endpoints = {endpoint['id']: endpoint for endpoint in discover_api_endpoints()}
        item_catalog = endpoints['api/items/']
        match_suggestions = endpoints['api/match-suggestions/']

        self.assertEqual(item_catalog['methods'], list(HTTP_METHODS))
        self.assertEqual(item_catalog['query_parameters'], ['q', 'type', 'category', 'page'])
        self.assertIn('image', match_suggestions['body_parameters'])
        self.assertNotIn(CONTROL_PREFIX, endpoints)


class APIEndpointContractTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='api-test-admin', password='TestPassword123!')
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save(update_fields=['role'])
        self.member = User.objects.create_user(username='api-test-member', password='TestPassword123!')

    def test_session_endpoint_reports_anonymous_state(self):
        response = self.client.get('/api/session/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'authenticated': False})

    def test_items_endpoint_returns_public_catalog_without_private_pickup_fields(self):
        response = self.client.get('/api/items/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.json())
        for item in response.json()['results']:
            self.assertEqual(item['building'], '')
            self.assertEqual(item['room'], '')
            self.assertEqual(item['workstation'], '')

    def test_matching_endpoint_requires_authentication_and_validates_uploads(self):
        response = self.client.post('/api/match-suggestions/', data={})
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.member)
        invalid_image = SimpleUploadedFile('invalid.png', b'not an image', content_type='image/png')
        response = self.client.post('/api/match-suggestions/', data={'image': invalid_image})
        self.assertEqual(response.status_code, 400)
        self.assertIn('detail', response.json())

        initial_count = Item.objects.count()
        response = self.client.post('/api/match-suggestions/', data={
            'item_type': 'FOUND',
            'title': 'Found wallet',
            'description': 'Brown leather wallet with a visible blue tag',
            'location': 'Main Building',
            'date_occurred': '2026-10-25',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.json())
        self.assertEqual(Item.objects.count(), initial_count)

    def test_admin_action_enforces_authentication_and_role(self):
        path = '/api/admin/test-action/'
        anonymous = self.client.post(path, data={})
        self.assertEqual(anonymous.status_code, 302)

        self.client.force_login(self.member)
        member_response = self.client.post(path, data={})
        self.assertEqual(member_response.status_code, 403)

        self.client.force_login(self.admin)
        admin_response = self.client.post(path, data={})
        self.assertEqual(admin_response.status_code, 405)
        self.assertIn('POST', admin_response.headers.get('Allow', ''))

    def test_method_matrix_rolls_back_database_changes(self):
        initial_count = Item.objects.count()
        with transaction.atomic():
            response = _request(Client(), 'POST', '/api/match-suggestions/', {})
            transaction.set_rollback(True)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(Item.objects.count(), initial_count)


class APIEndpointCSRFTests(TestCase):
    def test_state_changing_api_request_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post('/api/match-suggestions/', data={})
        self.assertEqual(response.status_code, 403)


class APIConsoleAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='console-admin', password='TestPassword123!')
        self.admin.profile.role = Profile.ROLE_ADMIN
        self.admin.profile.save(update_fields=['role'])
        self.member = User.objects.create_user(username='console-member', password='TestPassword123!')

    def test_console_and_run_api_require_administrator(self):
        with patch('api_testing.views._enabled', return_value=True):
            self.assertEqual(self.client.get('/api/test-console/').status_code, 401)
            self.client.force_login(self.member)
            self.assertEqual(self.client.get('/api/test-console/').status_code, 403)
            self.assertEqual(self.client.post('/api/test-console/run/', data='{}', content_type='application/json').status_code, 403)

    def test_console_is_hidden_when_testing_is_disabled(self):
        self.client.force_login(self.admin)
        with patch('api_testing.views._enabled', return_value=False):
            response = self.client.get('/api/test-console/')
        self.assertEqual(response.status_code, 404)

    def test_admin_can_load_discovered_endpoints_and_history(self):
        self.client.force_login(self.admin)
        with patch('api_testing.views._enabled', return_value=True):
            response = self.client.get('/api/test-console/')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['endpoints']), 7)
        self.assertTrue(all(len(endpoint['methods']) == 7 for endpoint in data['endpoints']))
        self.assertEqual(data['history'], [])
        self.assertFalse(any(endpoint['id'].startswith('api/test-console/') for endpoint in data['endpoints']))

    def test_run_api_rejects_invalid_json_and_unknown_endpoints(self):
        self.client.force_login(self.admin)
        with patch('api_testing.views._enabled', return_value=True):
            malformed = self.client.post('/api/test-console/run/', data='{', content_type='application/json')
            unknown = self.client.post(
                '/api/test-console/run/',
                data=json.dumps({'endpoint_id': 'https://example.invalid'}),
                content_type='application/json',
            )
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(ApiTestRun.objects.count(), 0)

    def test_run_api_persists_results_and_returns_run_history(self):
        from . import tests as api_tests

        self.addCleanup(api_tests.PROBE_RESULTS.clear)
        api_tests.PROBE_RESULTS.clear()
        api_tests.PROBE_RESULTS.append({
            'endpoint_id': 'api/items/',
            'endpoint': '/api/items/',
            'method': 'GET',
            'request': {'path': '/api/items/', 'path_parameters': [], 'query_parameters': {}, 'payload': None},
            'response': {'status': 200, 'headers': {'Content-Type': 'application/json'}, 'body': '{"results": []}'},
            'duration_ms': 2.0,
            'database_changed': False,
            'status_result': 'passed',
            'error': '',
        })
        self.client.force_login(self.admin)
        with (
            patch('api_testing.views._enabled', return_value=True),
            patch('api_testing.views._run_lock') as run_lock,
            patch('api_testing.tests.configure_probe'),
            patch('django.test.runner.DiscoverRunner.run_tests', return_value=0),
        ):
            run_lock.acquire.return_value = True
            response = self.client.post(
                '/api/test-console/run/',
                data=json.dumps({'endpoint_id': 'api/items/', 'method': 'GET'}),
                content_type='application/json',
            )
            if response.status_code == 200:
                run_id = response.json()['run']['id']
                detail = self.client.get(f'/api/test-console/runs/{run_id}/')

        self.assertEqual(response.status_code, 200)
        run_data = response.json()['run']
        self.assertEqual(run_data['status'], ApiTestRun.STATUS_PASSED)
        self.assertEqual(run_data['results'][0]['response']['status'], 200)
        self.assertEqual(ApiTestRun.objects.get(pk=run_data['id']).requested_by, self.admin.username)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()['run']['results'][0]['method'], 'GET')
