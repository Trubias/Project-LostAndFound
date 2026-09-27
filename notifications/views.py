from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404

from .models import Notification


def _get_user_notification_or_404(user, notification_id):
    """Return the notification only if it belongs to *user*, else raise 404."""
    notification = get_object_or_404(Notification, pk=notification_id)
    if notification.recipient != user:
        raise Http404("Notification not found.")
    return notification


# ── Notification List ─────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def notification_list_view(request):
    """Show all notifications for the logged-in user with optional filter."""
    notifications_qs = Notification.objects.filter(
        recipient=request.user
    ).select_related('related_item', 'related_claim')

    # Filter by read/unread
    read_filter = request.GET.get('filter', '').strip().lower()
    if read_filter == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)
    elif read_filter == 'read':
        notifications_qs = notifications_qs.filter(is_read=True)

    paginator = Paginator(notifications_qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    return render(request, 'notifications/notification_list.html', {
        'notifications': page_obj,
        'page_obj': page_obj,
        'unread_count': unread_count,
        'read_filter': read_filter,
    })


# ── Notification Detail ───────────────────────────────────────────────────────

@login_required(login_url='/login/')
def notification_detail_view(request, notification_id):
    """Show a single notification; mark it as read on access."""
    notification = _get_user_notification_or_404(request.user, notification_id)

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    return render(request, 'notifications/notification_detail.html', {
        'notification': notification,
    })


# ── Mark as Read ──────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def mark_as_read_view(request, notification_id):
    """Mark a single notification as read (POST only)."""
    if request.method != 'POST':
        return redirect('notifications:list')

    notification = _get_user_notification_or_404(request.user, notification_id)
    notification.is_read = True
    notification.save(update_fields=['is_read'])

    next_url = request.POST.get('next') or 'notifications:list'
    return redirect(next_url)


# ── Mark All as Read ──────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def mark_all_read_view(request):
    """Mark ALL of the current user's unread notifications as read (POST only)."""
    if request.method != 'POST':
        return redirect('notifications:list')

    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)

    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')


# ── Delete Notification ───────────────────────────────────────────────────────

@login_required(login_url='/login/')
def delete_notification_view(request, notification_id):
    """Delete a notification belonging to the current user (POST only)."""
    if request.method != 'POST':
        return redirect('notifications:list')

    notification = _get_user_notification_or_404(request.user, notification_id)
    notification.delete()
    messages.success(request, 'Notification deleted.')
    return redirect('notifications:list')
