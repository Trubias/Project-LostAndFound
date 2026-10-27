"""POST-only admin actions used by the Next.js admin workspace."""
import re

from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile
from items.forms import FoundReportForm, CategoryForm, ReportLocationForm
from items.models import Category, Item, ReportLocation
from matches.models import ItemMatch
from auditlog.services import record_event
from notifications import services as notification_services
from notifications.models import Notification
from reports.models import AbuseReport


def _is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(getattr(user, 'profile', None), 'role', None) == Profile.ROLE_ADMIN
    )


@require_POST
def admin_action(request, action):
    if not request.user.is_authenticated:
        return redirect('/login/')
    if not _is_admin(request.user):
        return HttpResponseForbidden('Administrator access required.')

    notification_read = re.fullmatch(r'notifications/(\d+)/read', action)
    if notification_read:
        notification = get_object_or_404(Notification, pk=notification_read.group(1))
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return JsonResponse({'detail': 'Notification marked as read.'})

    mark_found = re.fullmatch(r'items/(\d+)/mark-found', action)
    if mark_found:
        form = FoundReportForm(request.POST, request.FILES)
        with transaction.atomic():
            item = get_object_or_404(
                Item.objects.select_for_update(),
                pk=mark_found.group(1),
            )
            if item.item_type != Item.TYPE_LOST or item.status != Item.STATUS_ACTIVE:
                return JsonResponse(
                    {'detail': 'Only active lost reports can be marked as found.'},
                    status=409,
                )
            if not form.is_valid():
                return JsonResponse({'detail': 'Please provide a valid finding description and photo.'}, status=400)
            item.item_type = Item.TYPE_FOUND
            item.status = Item.STATUS_ACTIVE
            item.found_by = request.user
            item.found_at = timezone.now()
            item.found_description = form.cleaned_data['found_description']
            item.found_image = form.cleaned_data['found_image']
            item.save(update_fields=[
                'item_type', 'status', 'found_by', 'found_at',
                'found_description', 'found_image', 'updated_at',
            ])
            record_event(
                request.user,
                'item.found_reported',
                item,
                f'@{request.user.username} reported finding "{item.title}".',
            )
            notification_services.notify_item_found(item, request.user)
        return redirect('/admin-dashboard/claims?updated=1')

    user_match = re.fullmatch(r'users/(\d+)/(toggle-status|change-role)', action)
    if user_match:
        target = get_object_or_404(User.objects.select_related('profile'), pk=user_match.group(1))
        operation = user_match.group(2)
        if target.pk == request.user.pk or target.is_superuser:
            return redirect(f'/admin-dashboard/users/{target.pk}?error=1')
        if operation == 'toggle-status':
            target.is_active = not target.is_active
            target.save(update_fields=['is_active'])
            record_event(request.user, 'user.status_changed', target, f'@{request.user.username} changed @{target.username} to {"active" if target.is_active else "inactive"}.')
        else:
            role = request.POST.get('role', '').strip().upper()
            if role not in (Profile.ROLE_USER, Profile.ROLE_ADMIN):
                return redirect(f'/admin-dashboard/users/{target.pk}/change-role?error=1')
            target.profile.role = role
            target.profile.save(update_fields=['role'])
            record_event(request.user, 'user.role_changed', target, f'@{request.user.username} changed @{target.username} role to {role}.')
        return redirect(f'/admin-dashboard/users/{target.pk}?updated=1')

    category_add = action == 'categories/add'
    category_edit = re.fullmatch(r'categories/(\d+)/edit', action)
    category_delete = re.fullmatch(r'categories/(\d+)/delete', action)
    if category_add or category_edit:
        category = get_object_or_404(Category, pk=category_edit.group(1)) if category_edit else None
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            saved_category = form.save()
            record_event(request.user, 'category.saved', saved_category, f'@{request.user.username} saved category "{saved_category.name}".')
            return redirect('/admin-dashboard/categories?updated=1')
        suffix = 'add' if category is None else f'{category.pk}/edit'
        return redirect(f'/admin-dashboard/categories/{suffix}?error=1')
    if category_delete:
        category = get_object_or_404(Category, pk=category_delete.group(1))
        if category.items.exists():
            return redirect(f'/admin-dashboard/categories/{category.pk}/delete?error=in-use')
        record_event(request.user, 'category.deleted', category, f'@{request.user.username} deleted category "{category.name}".')
        category.delete()
        return redirect('/admin-dashboard/categories?deleted=1')

    location_add = action == 'locations/add'
    location_edit = re.fullmatch(r'locations/(\d+)/edit', action)
    if location_add or location_edit:
        location = get_object_or_404(ReportLocation, pk=location_edit.group(1)) if location_edit else None
        form = ReportLocationForm(request.POST, instance=location)
        if form.is_valid():
            saved_location = form.save()
            record_event(request.user, 'location.saved', saved_location, f'@{request.user.username} saved report location "{saved_location.name}".')
            return redirect('/admin-dashboard/locations?updated=1')
        suffix = 'add' if location is None else f'{location.pk}/edit'
        return redirect(f'/admin-dashboard/locations/{suffix}?error=1')

    flag_action = re.fullmatch(r'flags/(\d+)/(review|dismiss)', action)
    if flag_action:
        flag = get_object_or_404(AbuseReport, pk=flag_action.group(1))
        if flag.status != AbuseReport.STATUS_OPEN:
            return redirect(f'/admin-dashboard/flags/{flag.pk}?error=closed')
        flag.status = AbuseReport.STATUS_REVIEWED if flag_action.group(2) == 'review' else AbuseReport.STATUS_DISMISSED
        flag.reviewed_by = request.user
        flag.reviewer_notes = request.POST.get('reviewer_notes', '').strip()[:2000]
        flag.save(update_fields=['status', 'reviewed_by', 'reviewer_notes', 'updated_at'])
        record_event(request.user, f'abuse_report.{flag.status.lower()}', flag, f'@{request.user.username} {flag.get_status_display().lower()} community report #{flag.pk}.')
        return redirect(f'/admin-dashboard/flags/{flag.pk}?updated=1')

    match_action = re.fullmatch(r'matches/(\d+)/(confirm|dismiss)', action)
    if match_action:
        match = get_object_or_404(ItemMatch, pk=match_action.group(1))
        match.status = ItemMatch.STATUS_CONFIRMED if match_action.group(2) == 'confirm' else ItemMatch.STATUS_DISMISSED
        match.save(update_fields=['status', 'updated_at'])
        record_event(request.user, f'match.{match.status.lower()}', match, f'@{request.user.username} marked match #{match.pk} {match.get_status_display().lower()}.')
        return redirect('/admin-dashboard/matches?updated=1')

    return HttpResponseNotAllowed(['POST'])
