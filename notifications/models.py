from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):
    """
    In-app notification for a user.

    Notifications are created by the notification service (notifications.services)
    and are never directly created in views or signals outside of that module.

    Fields:
        recipient      — the user who receives this notification
        notification_type — one of the TYPE_* constants defined below
        title          — short one-line heading shown in the notification list
        message        — full notification body text
        related_item   — optional FK to the affected Item (SET_NULL on delete)
        related_claim  — optional FK to the affected Claim (SET_NULL on delete)
        is_read        — True once the user has opened/acknowledged it
        created_at     — timestamp when the notification was generated
    """

    # ── Type constants ────────────────────────────────────────────
    TYPE_CLAIM_SUBMITTED = 'CLAIM_SUBMITTED'
    TYPE_CLAIM_APPROVED  = 'CLAIM_APPROVED'
    TYPE_CLAIM_REJECTED  = 'CLAIM_REJECTED'
    TYPE_CLAIM_WITHDRAWN = 'CLAIM_WITHDRAWN'
    TYPE_ITEM_ARCHIVED   = 'ITEM_ARCHIVED'
    TYPE_ITEM_RESTORED   = 'ITEM_RESTORED'
    TYPE_POSSIBLE_MATCH  = 'POSSIBLE_MATCH'
    TYPE_MATCH_CONFIRMED = 'MATCH_CONFIRMED'
    TYPE_SYSTEM          = 'SYSTEM'

    NOTIFICATION_TYPE_CHOICES = [
        (TYPE_CLAIM_SUBMITTED, 'Claim Submitted'),
        (TYPE_CLAIM_APPROVED,  'Claim Approved'),
        (TYPE_CLAIM_REJECTED,  'Claim Rejected'),
        (TYPE_CLAIM_WITHDRAWN, 'Claim Withdrawn'),
        (TYPE_ITEM_ARCHIVED,   'Item Archived'),
        (TYPE_ITEM_RESTORED,   'Item Restored'),
        (TYPE_POSSIBLE_MATCH,  'Possible Match Found'),
        (TYPE_MATCH_CONFIRMED, 'Match Confirmed'),
        (TYPE_SYSTEM,          'System Notification'),
    ]

    # ── Relationships ─────────────────────────────────────────────
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    related_item = models.ForeignKey(
        'items.Item',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )
    related_claim = models.ForeignKey(
        'claims.Claim',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
    )

    # ── Content ───────────────────────────────────────────────────
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPE_CHOICES,
        default=TYPE_SYSTEM,
    )
    title   = models.CharField(max_length=200)
    message = models.TextField()

    # ── State ─────────────────────────────────────────────────────
    is_read = models.BooleanField(default=False)

    # ── Timestamps ────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)

    # ── Helpers ───────────────────────────────────────────────────
    def get_icon(self):
        """Return a Bootstrap Icon class for the notification type."""
        icons = {
            self.TYPE_CLAIM_SUBMITTED: 'bi-hand-index-thumb-fill',
            self.TYPE_CLAIM_APPROVED:  'bi-check-circle-fill',
            self.TYPE_CLAIM_REJECTED:  'bi-x-circle-fill',
            self.TYPE_CLAIM_WITHDRAWN: 'bi-dash-circle-fill',
            self.TYPE_ITEM_ARCHIVED:   'bi-archive-fill',
            self.TYPE_ITEM_RESTORED:   'bi-arrow-counterclockwise',
            self.TYPE_POSSIBLE_MATCH:  'bi-lightning-fill',
            self.TYPE_MATCH_CONFIRMED: 'bi-patch-check-fill',
            self.TYPE_SYSTEM:          'bi-info-circle-fill',
        }
        return icons.get(self.notification_type, 'bi-bell-fill')

    def get_color(self):
        """Return a Bootstrap colour name for the notification type."""
        colours = {
            self.TYPE_CLAIM_SUBMITTED: 'info',
            self.TYPE_CLAIM_APPROVED:  'success',
            self.TYPE_CLAIM_REJECTED:  'danger',
            self.TYPE_CLAIM_WITHDRAWN: 'secondary',
            self.TYPE_ITEM_ARCHIVED:   'secondary',
            self.TYPE_ITEM_RESTORED:   'success',
            self.TYPE_POSSIBLE_MATCH:  'warning',
            self.TYPE_MATCH_CONFIRMED: 'success',
            self.TYPE_SYSTEM:          'primary',
        }
        return colours.get(self.notification_type, 'primary')

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → @{self.recipient.username}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
