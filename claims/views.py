from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from accounts.models import Profile
from items.models import Item
from .models import Claim
from .forms import ClaimForm, ReviewClaimForm
from notifications import services as notif_svc


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def is_admin_user(user):
    """Return True if the user has ADMIN role or is a Django superuser."""
    if user.is_superuser:
        return True
    try:
        return user.profile.role == Profile.ROLE_ADMIN
    except Profile.DoesNotExist:
        return False


def can_review_claim(user, claim):
    """
    A claim can be reviewed by:
      - The reporter of the item this claim is for.
      - Any admin user.
    """
    return claim.item.reporter == user or is_admin_user(user)


# ─────────────────────────────────────────────
# Submit Claim
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def submit_claim_view(request, item_id):
    """Allow an authenticated user to submit a claim for an active item."""
    item = get_object_or_404(Item, pk=item_id)

    # ── Server-side validation ──────────────────────────────────
    if item.reporter == request.user:
        messages.error(request, 'You cannot claim your own reported item.')
        return redirect('items:item_detail', pk=item.pk)

    if not item.is_active():
        messages.error(request, 'This item is no longer active and cannot be claimed.')
        return redirect('items:item_detail', pk=item.pk)

    # Check for existing pending claim from this user
    existing_pending = Claim.objects.filter(
        item=item,
        claimant=request.user,
        status=Claim.STATUS_PENDING
    ).exists()

    if existing_pending:
        messages.warning(
            request,
            'You already have a pending claim for this item. '
            'Please wait for it to be reviewed.'
        )
        return redirect('claims:my_claims')

    if request.method == 'POST':
        form = ClaimForm(request.POST)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.item = item
            claim.claimant = request.user
            claim.status = Claim.STATUS_PENDING  # Always PENDING on creation
            claim.save()
            # Notify the item reporter that a new claim has been submitted
            notif_svc.notify_claim_submitted(claim)
            messages.success(
                request,
                'Your claim has been submitted and is awaiting review.'
            )
            return redirect('claims:claim_detail', claim_id=claim.pk)
    else:
        form = ClaimForm()

    return render(request, 'claims/claim_form.html', {
        'form': form,
        'item': item,
    })


# ─────────────────────────────────────────────
# My Claims
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def my_claims_view(request):
    """Show all claims submitted by the currently logged-in user."""
    all_claims = Claim.objects.filter(claimant=request.user).select_related(
        'item', 'item__category', 'reviewed_by'
    )

    # Filter by status tab
    status_filter = request.GET.get('status', '').strip().upper()
    valid_statuses = [
        Claim.STATUS_PENDING,
        Claim.STATUS_APPROVED,
        Claim.STATUS_REJECTED,
        Claim.STATUS_WITHDRAWN,
    ]
    if status_filter in valid_statuses:
        claims = all_claims.filter(status=status_filter)
    else:
        status_filter = ''
        claims = all_claims

    counts = {
        'all': all_claims.count(),
        'pending': all_claims.filter(status=Claim.STATUS_PENDING).count(),
        'approved': all_claims.filter(status=Claim.STATUS_APPROVED).count(),
        'rejected': all_claims.filter(status=Claim.STATUS_REJECTED).count(),
        'withdrawn': all_claims.filter(status=Claim.STATUS_WITHDRAWN).count(),
    }

    return render(request, 'claims/my_claims.html', {
        'claims': claims,
        'counts': counts,
        'status_filter': status_filter,
    })


# ─────────────────────────────────────────────
# Claim Detail
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def claim_detail_view(request, claim_id):
    """
    Show claim detail.
    Accessible by: claimant, item reporter, or admin.
    """
    claim = get_object_or_404(Claim, pk=claim_id)

    is_claimant = claim.claimant == request.user
    is_item_reporter = claim.item.reporter == request.user
    is_admin = is_admin_user(request.user)

    if not (is_claimant or is_item_reporter or is_admin):
        messages.error(request, 'You do not have permission to view this claim.')
        return render(request, '403.html', status=403)

    return render(request, 'claims/claim_detail.html', {
        'claim': claim,
        'is_claimant': is_claimant,
        'is_item_reporter': is_item_reporter,
        'is_admin': is_admin,
        'can_review': can_review_claim(request.user, claim),
    })


# ─────────────────────────────────────────────
# Withdraw Claim
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def withdraw_claim_view(request, claim_id):
    """Allow the claimant to withdraw their own PENDING claim only."""
    claim = get_object_or_404(Claim, pk=claim_id)

    # Only the claimant can withdraw
    if claim.claimant != request.user:
        messages.error(request, 'You can only withdraw your own claims.')
        return render(request, '403.html', status=403)

    # Only PENDING claims can be withdrawn
    if not claim.is_pending():
        messages.error(
            request,
            f'Only pending claims can be withdrawn. '
            f'This claim is currently {claim.get_status_display()}.'
        )
        return redirect('claims:claim_detail', claim_id=claim.pk)

    if request.method == 'POST':
        claim.status = Claim.STATUS_WITHDRAWN
        claim.save()
        # Notify the item reporter that a claim was withdrawn
        notif_svc.notify_claim_withdrawn(claim)
        messages.success(request, 'Your claim has been withdrawn.')
        return redirect('claims:my_claims')

    return render(request, 'claims/confirm_withdraw.html', {'claim': claim})


# ─────────────────────────────────────────────
# Review Claim (item reporter or admin)
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def review_claim_view(request, claim_id):
    """
    Allow the item reporter or an admin to review (approve/reject) a claim.
    Only PENDING claims can be reviewed.
    """
    claim = get_object_or_404(Claim, pk=claim_id)

    # Permission check
    if not can_review_claim(request.user, claim):
        messages.error(request, 'You do not have permission to review this claim.')
        return render(request, '403.html', status=403)

    # Only pending claims can be reviewed
    if not claim.is_pending():
        messages.warning(
            request,
            f'This claim has already been {claim.get_status_display().lower()} '
            f'and cannot be reviewed again.'
        )
        return redirect('claims:claim_detail', claim_id=claim.pk)

    if request.method == 'POST':
        form = ReviewClaimForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            reviewer_notes = form.cleaned_data.get('reviewer_notes', '').strip()

            if action == 'approve':
                _approve_claim(claim, request.user, reviewer_notes)
                messages.success(
                    request,
                    f'Claim approved. The item "{claim.item.title}" has been archived '
                    f'and other pending claims have been rejected.'
                )
            elif action == 'reject':
                _reject_claim(claim, request.user, reviewer_notes)
                messages.success(request, 'Claim has been rejected.')

            return redirect('claims:claim_detail', claim_id=claim.pk)
    else:
        form = ReviewClaimForm()

    # Other pending claims for the same item
    other_pending = Claim.objects.filter(
        item=claim.item,
        status=Claim.STATUS_PENDING
    ).exclude(pk=claim.pk)

    return render(request, 'claims/review_claim.html', {
        'claim': claim,
        'form': form,
        'other_pending_count': other_pending.count(),
    })


def _approve_claim(claim, reviewer, notes):
    """Internal: approve the claim, archive the item, reject all other pending claims."""
    now = timezone.now()

    # Approve this claim
    claim.status = Claim.STATUS_APPROVED
    claim.reviewed_by = reviewer
    claim.reviewer_notes = notes
    claim.reviewed_at = now
    claim.save()

    # Archive the item
    item = claim.item
    item.status = Item.STATUS_ARCHIVED
    item.save()

    # Reject all other pending claims for this item
    other_pending = Claim.objects.filter(
        item=item,
        status=Claim.STATUS_PENDING
    ).exclude(pk=claim.pk)

    other_rejected_ids = list(other_pending.values_list('pk', flat=True))
    other_pending.update(
        status=Claim.STATUS_REJECTED,
        reviewed_by=reviewer,
        reviewer_notes='This item has already been resolved through another approved claim.',
        reviewed_at=now,
    )

    # Send notifications
    notif_svc.notify_claim_approved(claim)
    notif_svc.notify_item_archived(item, triggering_user=reviewer)

    # Notify the other claimants whose claims were rejected
    for rejected_claim in Claim.objects.filter(pk__in=other_rejected_ids):
        notif_svc.notify_claim_rejected(rejected_claim)


def _reject_claim(claim, reviewer, notes):
    """Internal: reject the claim."""
    claim.status = Claim.STATUS_REJECTED
    claim.reviewed_by = reviewer
    claim.reviewer_notes = notes
    claim.reviewed_at = timezone.now()
    claim.save()
    # Notify the claimant
    notif_svc.notify_claim_rejected(claim)


# ─────────────────────────────────────────────
# Claims for a Specific Item (item reporter / admin)
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def item_claims_view(request, item_id):
    """
    Show all claims submitted for a specific item.
    Only the item's reporter or an admin may access this page.
    """
    item = get_object_or_404(Item, pk=item_id)

    if item.reporter != request.user and not is_admin_user(request.user):
        messages.error(request, 'You do not have permission to view claims for this item.')
        return render(request, '403.html', status=403)

    item_claims = Claim.objects.filter(item=item).select_related('claimant', 'reviewed_by')

    return render(request, 'claims/item_claims.html', {
        'item': item,
        'item_claims': item_claims,
        'pending_count': item_claims.filter(status=Claim.STATUS_PENDING).count(),
    })


# ─────────────────────────────────────────────
# Admin: All Claims List
# ─────────────────────────────────────────────

@login_required(login_url='/login/')
def claim_list_view(request):
    """Admin-only view showing all claims across the system."""
    if not is_admin_user(request.user):
        messages.error(request, 'Only administrators can view all claims.')
        return render(request, '403.html', status=403)

    all_claims = Claim.objects.select_related(
        'item', 'item__category', 'claimant', 'reviewed_by'
    )

    # Filter by status
    status_filter = request.GET.get('status', '').strip().upper()
    valid_statuses = [
        Claim.STATUS_PENDING,
        Claim.STATUS_APPROVED,
        Claim.STATUS_REJECTED,
        Claim.STATUS_WITHDRAWN,
    ]
    if status_filter in valid_statuses:
        claims = all_claims.filter(status=status_filter)
    else:
        status_filter = ''
        claims = all_claims

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        claims = claims.filter(
            Q(item__title__icontains=q) |
            Q(claimant__username__icontains=q) |
            Q(claimant__email__icontains=q) |
            Q(message__icontains=q) |
            Q(proof_description__icontains=q)
        )

    counts = {
        'all': all_claims.count(),
        'pending': all_claims.filter(status=Claim.STATUS_PENDING).count(),
        'approved': all_claims.filter(status=Claim.STATUS_APPROVED).count(),
        'rejected': all_claims.filter(status=Claim.STATUS_REJECTED).count(),
        'withdrawn': all_claims.filter(status=Claim.STATUS_WITHDRAWN).count(),
    }

    return render(request, 'claims/claim_list.html', {
        'claims': claims,
        'counts': counts,
        'status_filter': status_filter,
        'q': q,
    })
