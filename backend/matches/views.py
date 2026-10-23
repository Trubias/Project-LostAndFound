from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404

from .models import ItemMatch
from notifications import services as notif_svc


def _get_user_match_or_404(user, match_id):
    """
    Return match only if the user is the reporter of the lost item
    OR the found item, or if the user is an admin.
    """
    match = get_object_or_404(ItemMatch, pk=match_id)
    is_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin())
    if not (match.involves_user(user) or is_admin):
        raise Http404("Match not found.")
    return match


# ── Matches List ──────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def match_list_view(request):
    """
    Show possible matches involving the user's reported items (lost or found).
    """
    matches_qs = ItemMatch.objects.filter(
        Q(lost_item__reporter=request.user) | Q(found_item__reporter=request.user)
    ).select_related(
        'lost_item', 'lost_item__category',
        'found_item', 'found_item__category'
    )

    status_filter = request.GET.get('status', '').strip().upper()
    if status_filter in [ItemMatch.STATUS_PENDING, ItemMatch.STATUS_CONFIRMED, ItemMatch.STATUS_DISMISSED]:
        matches_qs = matches_qs.filter(status=status_filter)

    paginator = Paginator(matches_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    total_pending = ItemMatch.objects.filter(
        Q(lost_item__reporter=request.user) | Q(found_item__reporter=request.user),
        status=ItemMatch.STATUS_PENDING
    ).count()

    return render(request, 'matches/match_list.html', {
        'matches': page_obj,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'total_pending': total_pending,
    })


# ── Match Detail ──────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def match_detail_view(request, match_id):
    """
    Detailed comparison between Lost Item and Found Item, plus score breakdown.
    """
    match = _get_user_match_or_404(request.user, match_id)
    is_involved = match.involves_user(request.user)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.is_admin())

    return render(request, 'matches/match_detail.html', {
        'match': match,
        'is_involved': is_involved,
        'is_admin': is_admin,
    })


# ── Confirm Match ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def confirm_match_view(request, match_id):
    """
    Confirm a match (change PENDING -> CONFIRMED).
    Can only be confirmed by one of the involved reporters or an admin.
    """
    if request.method != 'POST':
        return redirect('matches:detail', match_id=match_id)

    match = _get_user_match_or_404(request.user, match_id)
    if not match.is_pending():
        messages.warning(request, f'This match is already {match.get_status_display().lower()}.')
        return redirect('matches:detail', match_id=match.pk)

    match.status = ItemMatch.STATUS_CONFIRMED
    match.save(update_fields=['status', 'updated_at'])

    # Send notification to the other party
    notif_svc.notify_match_confirmed(match, confirming_user=request.user)

    messages.success(request, 'Match confirmed! You may now submit or review a formal claim to verify ownership.')
    return redirect('matches:detail', match_id=match.pk)


# ── Dismiss Match ─────────────────────────────────────────────────────────────

@login_required(login_url='/login/')
def dismiss_match_view(request, match_id):
    """
    Dismiss a match (change PENDING -> DISMISSED).
    """
    if request.method != 'POST':
        return redirect('matches:detail', match_id=match_id)

    match = _get_user_match_or_404(request.user, match_id)
    if not match.is_pending():
        messages.warning(request, f'This match is already {match.get_status_display().lower()}.')
        return redirect('matches:detail', match_id=match.pk)

    match.status = ItemMatch.STATUS_DISMISSED
    match.save(update_fields=['status', 'updated_at'])

    messages.info(request, 'Match dismissed.')
    return redirect('matches:list')
