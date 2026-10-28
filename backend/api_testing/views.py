import json
import socket
import threading
import time
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Profile

from .catalog import HTTP_METHODS, discover_api_endpoints
from .models import ApiTestRun


_run_lock = threading.Lock()


def _enabled():
    return (
        settings.API_TESTING_ENABLED
        and settings.DEBUG
        and not settings.IS_PRODUCTION
        and settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3'
    )


def _authorize(request):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Authentication required.'}, status=401)
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_superuser and not (profile and profile.role == Profile.ROLE_ADMIN):
        return JsonResponse({'detail': 'Administrator access required.'}, status=403)
    return None


def _run_data(run, include_results=True):
    data = {
        'id': run.pk,
        'status': run.status,
        'requested_by': run.requested_by,
        'endpoint_id': run.endpoint_id,
        'http_method': run.http_method,
        'started_at': run.started_at.isoformat(),
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        'duration_ms': run.duration_ms,
        'passed_count': run.passed_count,
        'failed_count': run.failed_count,
    }
    if include_results:
        data['results'] = run.results
        data['output'] = run.output
    return data


def _unavailable():
    return JsonResponse({'detail': 'The API test console is only available in local SQLite debug mode.'}, status=404)


@require_GET
def console_view(request):
    if not _enabled():
        return _unavailable()
    denied = _authorize(request)
    if denied:
        return denied

    runs = ApiTestRun.objects.all()[:20]
    endpoints = discover_api_endpoints()
    latest_results = {}
    latest_run = ApiTestRun.objects.exclude(results=[]).first()
    if latest_run:
        latest_results = {
            (result.get('endpoint_id'), result.get('method')): result
            for result in latest_run.results
            if isinstance(result, dict)
        }
    for endpoint in endpoints:
        endpoint['last_results'] = {
            method: latest_results.get((endpoint['id'], method))
            for method in HTTP_METHODS
            if latest_results.get((endpoint['id'], method))
        }
    return JsonResponse({
        'endpoints': endpoints,
        'history': [_run_data(run, include_results=False) for run in runs],
    })


@require_GET
def run_list_view(request):
    if not _enabled():
        return _unavailable()
    denied = _authorize(request)
    if denied:
        return denied
    runs = ApiTestRun.objects.all()[:50]
    return JsonResponse({'runs': [_run_data(run, include_results=False) for run in runs]})


@require_GET
def run_detail_view(request, run_id):
    if not _enabled():
        return _unavailable()
    denied = _authorize(request)
    if denied:
        return denied
    try:
        run = ApiTestRun.objects.get(pk=run_id)
    except ApiTestRun.DoesNotExist:
        return JsonResponse({'detail': 'Test run not found.'}, status=404)
    return JsonResponse({'run': _run_data(run)})


@require_POST
def start_run_view(request):
    if not _enabled():
        return _unavailable()
    denied = _authorize(request)
    if denied:
        return denied

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'detail': 'Request body must be valid JSON.'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'detail': 'Request body must be a JSON object.'}, status=400)

    endpoint_id = str(payload.get('endpoint_id', '')).strip()
    method = str(payload.get('method', '')).strip().upper()
    run_all = payload.get('all') is True
    if run_all:
        endpoint_id = ''
        method = ''
    elif endpoint_id not in {endpoint['id'] for endpoint in discover_api_endpoints()}:
        return JsonResponse({'detail': 'Select a discovered API endpoint.'}, status=400)
    if method and method not in HTTP_METHODS:
        return JsonResponse({'detail': 'Select a supported HTTP method.'}, status=400)

    if not _run_lock.acquire(blocking=False):
        return JsonResponse({'detail': 'An API test run is already in progress.'}, status=409)

    try:
        run = ApiTestRun.objects.create(
            requested_by=request.user.get_username(),
            endpoint_id=endpoint_id,
            http_method=method,
        )
    except Exception:
        _run_lock.release()
        raise
    started = time.perf_counter()
    output = StringIO()
    results = []
    failed_count = 0
    try:
        from django.test.runner import DiscoverRunner

        from . import tests as api_tests

        api_tests.configure_probe(endpoint_id, method)
        runner = DiscoverRunner(verbosity=2, interactive=False, keepdb=False)
        test_labels = (
            ['api_testing.tests']
            if not endpoint_id
            else ['api_testing.tests.APIEndpointMethodSmokeTests.test_discovered_api_routes_and_methods']
        )
        with (
            redirect_stdout(output),
            redirect_stderr(output),
            patch.object(socket.socket, 'connect', side_effect=RuntimeError('Outbound network access is disabled during API tests.')),
            patch.object(socket.socket, 'connect_ex', side_effect=RuntimeError('Outbound network access is disabled during API tests.')),
        ):
            failed_count = runner.run_tests(test_labels)
        results = list(api_tests.PROBE_RESULTS)
    except Exception as exc:
        failed_count += 1
        output.write(f'{type(exc).__name__}: {exc}\n')
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000)
        passed_count = sum(result['status_result'] == 'passed' for result in results)
        if failed_count == 0:
            run.status = ApiTestRun.STATUS_PASSED
        else:
            run.status = ApiTestRun.STATUS_FAILED
        run.completed_at = timezone.now()
        run.duration_ms = duration_ms
        run.passed_count = passed_count
        run.failed_count = failed_count
        run.results = results
        run.output = output.getvalue()[-20000:]
        try:
            run.save(update_fields=[
                'status', 'completed_at', 'duration_ms', 'passed_count',
                'failed_count', 'results', 'output',
            ])
        finally:
            _run_lock.release()

    return JsonResponse({'run': _run_data(run)}, status=200)
