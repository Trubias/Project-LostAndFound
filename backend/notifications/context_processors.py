from .models import Notification
from matches.models import ItemMatch
from django.db.models import Q


def notification_counts(request):
    """
    Context processor to make unread notification count and pending matches count
    available across all templates.
    """
    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0,
            'user_pending_matches_count': 0,
        }

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    pending_matches_count = ItemMatch.objects.filter(
        Q(lost_item__reporter=request.user) | Q(found_item__reporter=request.user),
        status=ItemMatch.STATUS_PENDING
    ).count()

    return {
        'unread_notifications_count': unread_count,
        'user_pending_matches_count': pending_matches_count,
    }
