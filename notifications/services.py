"""
Notification service for the Lost & Found system.

All notification creation goes through create_notification().
This prevents duplicate notification code scattered across views and signals,
and makes it easy to add email delivery in the future.

Duplication prevention:
    Each helper checks whether an identical notification already exists
    for the same (recipient, notification_type, related_item, related_claim)
    before creating a new one.
"""

from .models import Notification


def create_notification(
    recipient,
    notification_type,
    title,
    message,
    related_item=None,
    related_claim=None,
):
    """
    Create a Notification for *recipient* unless an identical one already exists.

    Returns the Notification instance (existing or newly created) and a boolean
    flag indicating whether it was created (True) or already existed (False).

    This is the single entry-point for notification creation — use this
    everywhere rather than Notification.objects.create() directly.
    """
    existing = Notification.objects.filter(
        recipient=recipient,
        notification_type=notification_type,
        related_item=related_item,
        related_claim=related_claim,
    ).first()

    if existing:
        return existing, False

    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_item=related_item,
        related_claim=related_claim,
    )
    return notification, True


# ── Claim notifications ───────────────────────────────────────────────────────

def notify_claim_submitted(claim):
    """
    Notify the item reporter that a new claim has been submitted for their item.
    Called immediately after a Claim object is created.
    """
    return create_notification(
        recipient=claim.item.reporter,
        notification_type=Notification.TYPE_CLAIM_SUBMITTED,
        title='New Claim Submitted',
        message=(
            f'@{claim.claimant.username} submitted a claim for your '
            f'{"lost" if claim.item.is_lost() else "found"} item '
            f'"{claim.item.title}". Please review it at your earliest convenience.'
        ),
        related_item=claim.item,
        related_claim=claim,
    )


def notify_claim_approved(claim):
    """
    Notify the claimant that their claim has been approved.
    Called after a claim's status is changed to APPROVED.
    """
    return create_notification(
        recipient=claim.claimant,
        notification_type=Notification.TYPE_CLAIM_APPROVED,
        title='Your Claim Has Been Approved',
        message=(
            f'Great news! Your claim for the item "{claim.item.title}" '
            f'has been approved. The item has been marked as resolved.'
        ),
        related_item=claim.item,
        related_claim=claim,
    )


def notify_claim_rejected(claim):
    """
    Notify the claimant that their claim has been rejected.
    Called after a claim's status is changed to REJECTED.
    """
    return create_notification(
        recipient=claim.claimant,
        notification_type=Notification.TYPE_CLAIM_REJECTED,
        title='Your Claim Has Been Rejected',
        message=(
            f'Unfortunately, your claim for the item "{claim.item.title}" '
            f'has been rejected. If you believe this is a mistake, you may '
            f'contact the item reporter directly or submit a new claim with '
            f'additional proof.'
        ),
        related_item=claim.item,
        related_claim=claim,
    )


def notify_claim_withdrawn(claim):
    """
    Notify the item reporter that a claimant withdrew their claim.
    Called after a claim's status is changed to WITHDRAWN.
    """
    return create_notification(
        recipient=claim.item.reporter,
        notification_type=Notification.TYPE_CLAIM_WITHDRAWN,
        title='A Claim Was Withdrawn',
        message=(
            f'@{claim.claimant.username} has withdrawn their claim for '
            f'your item "{claim.item.title}".'
        ),
        related_item=claim.item,
        related_claim=claim,
    )


# ── Item notifications ────────────────────────────────────────────────────────

def notify_item_archived(item, triggering_user=None):
    """
    Notify the item reporter that their item has been archived.
    Only sent when the reporter did not initiate the archive themselves.
    """
    if triggering_user and triggering_user == item.reporter:
        return None, False  # Reporter archived it themselves — no need to notify

    return create_notification(
        recipient=item.reporter,
        notification_type=Notification.TYPE_ITEM_ARCHIVED,
        title='Your Item Has Been Archived',
        message=(
            f'Your item "{item.title}" has been archived. '
            f'This usually means an approved claim has resolved the report.'
        ),
        related_item=item,
    )


def notify_item_restored(item, triggering_user=None):
    """
    Notify the item reporter that their item has been restored to active.
    Only sent when the reporter did not initiate the restoration themselves.
    """
    if triggering_user and triggering_user == item.reporter:
        return None, False

    return create_notification(
        recipient=item.reporter,
        notification_type=Notification.TYPE_ITEM_RESTORED,
        title='Your Item Has Been Restored',
        message=(
            f'Your item "{item.title}" has been restored to active status '
            f'and is now visible in the Lost & Found listings again.'
        ),
        related_item=item,
    )


# ── Match notifications ───────────────────────────────────────────────────────

def notify_possible_match(match):
    """
    Notify both the lost-item reporter and the found-item reporter that
    a possible match has been detected.

    Sends at most one notification per (match, reporter) pair.
    """
    lost_notif, _ = create_notification(
        recipient=match.lost_item.reporter,
        notification_type=Notification.TYPE_POSSIBLE_MATCH,
        title='Possible Match Found for Your Lost Item',
        message=(
            f'We found a possible match between your lost item '
            f'"{match.lost_item.title}" and a found item '
            f'"{match.found_item.title}". '
            f'The match score is {match.score}/100. '
            f'Review the match to confirm or dismiss it.'
        ),
        related_item=match.lost_item,
    )

    found_notif, _ = create_notification(
        recipient=match.found_item.reporter,
        notification_type=Notification.TYPE_POSSIBLE_MATCH,
        title='Possible Match Found for Your Found Item',
        message=(
            f'We found a possible match between the found item you reported '
            f'"{match.found_item.title}" and a lost item '
            f'"{match.lost_item.title}". '
            f'The match score is {match.score}/100. '
            f'Review the match to confirm or dismiss it.'
        ),
        related_item=match.found_item,
    )

    return lost_notif, found_notif


def notify_match_confirmed(match, confirming_user):
    """
    Notify the *other* party when one reporter confirms the match.
    E.g. if the lost-item reporter confirms, notify the found-item reporter.
    """
    other_reporter = (
        match.found_item.reporter
        if confirming_user == match.lost_item.reporter
        else match.lost_item.reporter
    )

    return create_notification(
        recipient=other_reporter,
        notification_type=Notification.TYPE_MATCH_CONFIRMED,
        title='A Match Has Been Confirmed',
        message=(
            f'@{confirming_user.username} confirmed the possible match between '
            f'"{match.lost_item.title}" and "{match.found_item.title}". '
            f'You may now proceed through the Claims workflow to verify ownership.'
        ),
        related_item=(
            match.found_item
            if other_reporter == match.found_item.reporter
            else match.lost_item
        ),
    )
