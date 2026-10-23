from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Q

from accounts.models import Profile
from items.models import Item
from .models import Claim
from .forms import ClaimForm, HandoffResponseForm, HandoffScheduleForm, ReviewClaimForm
from notifications import services as notif_svc
from auditlog.services import record_event


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

    if not item.is_active() or not item.is_found():
        messages.error(request, 'Only active found items can be claimed.')
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
            try:
                # The conditional unique constraint is the final guard for
                # two concurrent submissions that both passed `.exists()`.
                with transaction.atomic():
                    claim.save()
            except IntegrityError:
                messages.warning(
                    request,
                    'You already have a pending claim for this item. '
                    'Please wait for it to be reviewed.'
                )
                return redirect('claims:my_claims')
            # Notify the item reporter that a new claim has been submitted
            notif_svc.notify_claim_submitted(claim)
            record_event(request.user, 'claim.submitted', claim, f'@{request.user.username} submitted a claim for "{item.title}".')
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
                updated = _approve_claim(claim, request.user, reviewer_notes)
                if not updated:
                    messages.warning(request, 'This claim was already reviewed. No changes were made.')
                    return redirect('claims:claim_detail', claim_id=claim.pk)
                messages.success(
                    request,
                    f'Claim approved. The item "{claim.item.title}" has been archived '
                    f'and other pending claims have been rejected.'
                )
            elif action == 'reject':
                updated = _reject_claim(claim, request.user, reviewer_notes)
                if not updated:
                    messages.warning(request, 'This claim was already reviewed. No changes were made.')
                    return redirect('claims:claim_detail', claim_id=claim.pk)
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
    """Atomically approve one claim and close the other claims for its item."""
    item_id = Claim.objects.only('item_id').get(pk=claim.pk).item_id
    with transaction.atomic():
        # Locking the item serializes every review decision for this item,
        # including approvals of different claims.
        item = Item.objects.select_for_update().get(pk=item_id)
        claim = Claim.objects.select_for_update().select_related('claimant').get(pk=claim.pk)
        if not claim.is_pending() or not item.is_active() or not item.is_found():
            return False

        now = timezone.now()
        claim.status = Claim.STATUS_APPROVED
        claim.reviewed_by = reviewer
        claim.reviewer_notes = notes
        claim.reviewed_at = now
        claim.save(update_fields=['status', 'reviewed_by', 'reviewer_notes', 'reviewed_at', 'updated_at'])

        item.status = Item.STATUS_ARCHIVED
        item.save(update_fields=['status', 'updated_at'])

        other_pending = Claim.objects.filter(
            item=item, status=Claim.STATUS_PENDING
        ).exclude(pk=claim.pk)
        other_rejected_ids = list(other_pending.values_list('pk', flat=True))
        other_pending.update(
            status=Claim.STATUS_REJECTED,
            reviewed_by=reviewer,
            reviewer_notes='This item has already been resolved through another approved claim.',
            reviewed_at=now,
        )

        notif_svc.notify_claim_approved(claim)
        notif_svc.notify_item_archived(item, triggering_user=reviewer)
        record_event(reviewer, 'claim.approved', claim, f'Claim #{claim.pk} approved for "{item.title}".')
        for rejected_claim in Claim.objects.filter(pk__in=other_rejected_ids):
            notif_svc.notify_claim_rejected(rejected_claim)
        return True


def _reject_claim(claim, reviewer, notes):
    """Atomically reject a pending claim while serializing on its item."""
    item_id = Claim.objects.only('item_id').get(pk=claim.pk).item_id
    with transaction.atomic():
        Item.objects.select_for_update().get(pk=item_id)
        claim = Claim.objects.select_for_update().select_related('claimant').get(pk=claim.pk)
        if not claim.is_pending():
            return False
        claim.status = Claim.STATUS_REJECTED
        claim.reviewed_by = reviewer
        claim.reviewer_notes = notes
        claim.reviewed_at = timezone.now()
        claim.save(update_fields=['status', 'reviewed_by', 'reviewer_notes', 'reviewed_at', 'updated_at'])
        notif_svc.notify_claim_rejected(claim)
        record_event(reviewer, 'claim.rejected', claim, f'Claim #{claim.pk} rejected for "{claim.item.title}".')
        return True


def _record_handoff_confirmation(claim_id, confirmer):
    """Serialize party confirmations so concurrent handoff posts cannot overwrite one another."""
    with transaction.atomic():
        claim = Claim.objects.select_for_update().select_related('item', 'claimant').get(pk=claim_id)
        if (
            claim.status != Claim.STATUS_APPROVED
            or not claim.handoff_at
            or not claim.handoff_confirmed_by_claimant_at
            or claim.handoff_completed_at
        ):
            return claim, False

        is_claimant = claim.claimant_id == confirmer.pk
        is_reporter = claim.item.reporter_id == confirmer.pk
        if not (is_claimant or is_reporter):
            return claim, False

        field = 'handoff_returned_by_claimant_at' if is_claimant else 'handoff_returned_by_reporter_at'
        if getattr(claim, field):
            return claim, False

        setattr(claim, field, timezone.now())
        if claim.handoff_returned_by_claimant_at and claim.handoff_returned_by_reporter_at:
            claim.handoff_completed_at = timezone.now()
        claim.save(update_fields=[
            'handoff_returned_by_claimant_at', 'handoff_returned_by_reporter_at',
            'handoff_completed_at', 'updated_at',
        ])
        notif_svc.notify_handoff_returned(claim, confirmed_by=confirmer)
        record_event(confirmer, 'handoff.return_confirmed', claim, f'@{confirmer.username} confirmed the physical handoff for claim #{claim.pk}.')
        return claim, True


@login_required(login_url='/login/')
def schedule_handoff_view(request, claim_id):
    """Let the found-item reporter propose a public pickup appointment."""
    claim = get_object_or_404(Claim.objects.select_related('item', 'claimant'), pk=claim_id)
    if claim.status != Claim.STATUS_APPROVED:
        messages.error(request, 'A pickup plan is available after a claim is approved.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    if claim.item.reporter_id != request.user.pk and not is_admin_user(request.user):
        return render(request, '403.html', status=403)
    if claim.handoff_completed_at:
        messages.info(request, 'This item handoff has already been confirmed by both people.')
        return redirect('claims:claim_detail', claim_id=claim.pk)

    initial = None
    if claim.handoff_at:
        initial = {
            'handoff_location': claim.handoff_location,
            'handoff_at': timezone.localtime(claim.handoff_at).strftime('%Y-%m-%dT%H:%M'),
            'handoff_instructions': claim.handoff_instructions,
        }
    form = HandoffScheduleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            claim = Claim.objects.select_for_update().select_related('item', 'claimant').get(pk=claim_id)
            if claim.status != Claim.STATUS_APPROVED or claim.handoff_completed_at:
                messages.error(request, 'This claim is no longer available for a pickup plan.')
                return redirect('claims:claim_detail', claim_id=claim.pk)
            if form.cleaned_data['handoff_at'] <= timezone.now():
                form.add_error('handoff_at', 'Choose a future date and time.')
                return render(request, 'claims/handoff_schedule.html', {'claim': claim, 'form': form})
            claim.handoff_location = form.cleaned_data['handoff_location'].strip()
            claim.handoff_at = form.cleaned_data['handoff_at']
            claim.handoff_instructions = form.cleaned_data['handoff_instructions'].strip()
            claim.handoff_change_request = ''
            claim.handoff_confirmed_by_claimant_at = None
            claim.handoff_returned_by_claimant_at = None
            claim.handoff_returned_by_reporter_at = None
            claim.save(update_fields=[
                'handoff_location', 'handoff_at', 'handoff_instructions',
                'handoff_change_request', 'handoff_confirmed_by_claimant_at',
                'handoff_returned_by_claimant_at', 'handoff_returned_by_reporter_at', 'updated_at',
            ])
            notif_svc.notify_handoff_scheduled(claim)
            record_event(request.user, 'handoff.scheduled', claim, f'Pickup plan set for claim #{claim.pk} at {claim.handoff_location}.', {'handoff_at': claim.handoff_at.isoformat()})
        messages.success(request, 'Pickup plan saved. The claimant has been notified to confirm it.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    return render(request, 'claims/handoff_schedule.html', {'claim': claim, 'form': form})


@login_required(login_url='/login/')
def respond_handoff_view(request, claim_id):
    """Let the claimant confirm a proposed pickup plan or request a change."""
    claim = get_object_or_404(Claim.objects.select_related('item', 'claimant'), pk=claim_id)
    if claim.status != Claim.STATUS_APPROVED or not claim.handoff_at:
        messages.error(request, 'There is no active pickup plan to respond to.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    if claim.claimant_id != request.user.pk:
        return render(request, '403.html', status=403)
    if claim.handoff_completed_at:
        messages.info(request, 'This item handoff has already been confirmed by both people.')
        return redirect('claims:claim_detail', claim_id=claim.pk)

    form = HandoffResponseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            claim = Claim.objects.select_for_update().select_related('item', 'claimant').get(pk=claim_id)
            if claim.status != Claim.STATUS_APPROVED or not claim.handoff_at or claim.handoff_completed_at:
                messages.error(request, 'This pickup plan is no longer available for a response.')
                return redirect('claims:claim_detail', claim_id=claim.pk)
            if form.cleaned_data['action'] == 'confirm':
                claim.handoff_confirmed_by_claimant_at = timezone.now()
                claim.handoff_change_request = ''
                claim.save(update_fields=['handoff_confirmed_by_claimant_at', 'handoff_change_request', 'updated_at'])
                notif_svc.notify_handoff_confirmed(claim)
                record_event(request.user, 'handoff.plan_confirmed', claim, f'Claimant confirmed the pickup plan for claim #{claim.pk}.')
                messages.success(request, 'Pickup plan confirmed. Coordinate the handoff at the agreed public location.')
            else:
                claim.handoff_confirmed_by_claimant_at = None
                claim.handoff_change_request = form.cleaned_data['handoff_change_request'].strip()
                claim.handoff_returned_by_claimant_at = None
                claim.handoff_returned_by_reporter_at = None
                claim.save(update_fields=[
                    'handoff_confirmed_by_claimant_at', 'handoff_change_request',
                    'handoff_returned_by_claimant_at', 'handoff_returned_by_reporter_at', 'updated_at',
                ])
                notif_svc.notify_handoff_change_requested(claim)
                record_event(request.user, 'handoff.change_requested', claim, f'Claimant requested a pickup-plan change for claim #{claim.pk}.')
                messages.success(request, 'Your suggested change was sent to the item reporter.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    return render(request, 'claims/handoff_response.html', {'claim': claim, 'form': form})


@login_required(login_url='/login/')
def confirm_handoff_view(request, claim_id):
    """Record each party's confirmation that the physical item was handed over."""
    claim = get_object_or_404(Claim.objects.select_related('item', 'claimant'), pk=claim_id)
    if claim.status != Claim.STATUS_APPROVED or not claim.handoff_at:
        messages.error(request, 'The approved claim needs a pickup plan before the handoff can be confirmed.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    is_reporter = claim.item.reporter_id == request.user.pk
    is_claimant = claim.claimant_id == request.user.pk
    # Staff may review a case, but must not attest on behalf of either party.
    if not (is_reporter or is_claimant):
        return render(request, '403.html', status=403)
    if not claim.handoff_confirmed_by_claimant_at:
        messages.error(request, 'The claimant must confirm the pickup plan before recording the handoff.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    if request.method != 'POST':
        return render(request, 'claims/confirm_handoff.html', {'claim': claim})
    claim, changed = _record_handoff_confirmation(claim_id, request.user)
    if not changed:
        messages.info(request, 'This handoff confirmation was already recorded or is no longer available.')
        return redirect('claims:claim_detail', claim_id=claim.pk)
    if claim.handoff_completed_at:
        messages.success(request, 'Both people confirmed the return. The handoff is complete.')
    else:
        messages.success(request, 'Your confirmation was saved. The other person must confirm to complete the handoff.')
    return redirect('claims:claim_detail', claim_id=claim.pk)


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
