"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import DatabaseError, connection
from django.middleware.csrf import get_token
from django.views.decorators.http import require_GET
from items.views import api_items_view
from config.frontend_api import frontend_page_data
from config.admin_actions import admin_action
from config.matching_api import match_suggestions


def health_check(request):
    """Simple deployment health check endpoint."""
    return JsonResponse({'status': 'ok'})


@require_GET
def readiness_check(request):
    """Report whether the application can reach its configured database."""
    try:
        connection.ensure_connection()
    except DatabaseError:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})


@require_GET
def csrf_token_view(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_GET
def session_view(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'authenticated': False})
    profile = getattr(user, 'profile', None)
    is_admin = user.is_superuser or bool(profile and profile.role == 'ADMIN')
    avatar = profile.profile_image.url if profile and profile.profile_image else None
    return JsonResponse({
        'authenticated': True,
        'name': user.get_full_name() or user.username,
        'username': user.username,
        'avatar': avatar,
        'dashboard': '/admin-dashboard' if is_admin else '/dashboard',
        'isAdmin': is_admin,
    })


urlpatterns = [
    path('api/items/', api_items_view, name='api_items'),
    path('api/csrf/', csrf_token_view, name='csrf_token'),
    path('api/session/', session_view, name='session'),
    path('api/frontend-page/', frontend_page_data, name='frontend_page_data'),
    path('api/admin/<path:action>/', admin_action, name='frontend_admin_action'),
    path('api/match-suggestions/', match_suggestions, name='match_suggestions'),
    path('', include('api_testing.urls')),
    path('health/', health_check, name='health_check'),
    path('ready/', readiness_check, name='readiness_check'),
    path('admin/', admin.site.urls),
    path('', include('accounts.urls', namespace='accounts')),
    path('items/', include('items.urls', namespace='items')),
    path('claims/', include('claims.urls', namespace='claims')),
    path('notifications/', include('notifications.urls', namespace='notifications')),
    path('matches/', include('matches.urls', namespace='matches')),
    path('reports/', include('reports.urls', namespace='reports')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
