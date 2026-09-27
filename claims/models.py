from django.db import models
from django.contrib.auth.models import User
from items.models import Item


class Claim(models.Model):
    # ── Status choices ──────────────────────────────────────────
    STATUS_PENDING = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_WITHDRAWN = 'WITHDRAWN'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    # ── Relationships ────────────────────────────────────────────
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    claimant = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='claims'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claims'
    )

    # ── Claim details ────────────────────────────────────────────
    message = models.TextField(
        help_text='Explain why you believe this item belongs to you.'
    )
    proof_description = models.TextField(
        help_text='Describe unique identifying details (marks, contents, serial numbers, etc.).'
    )

    # ── Status & review ──────────────────────────────────────────
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    reviewer_notes = models.TextField(blank=True, null=True)

    # ── Timestamps ───────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # ── Helpers ──────────────────────────────────────────────────
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    def is_rejected(self):
        return self.status == self.STATUS_REJECTED

    def is_withdrawn(self):
        return self.status == self.STATUS_WITHDRAWN

    def get_status_badge_class(self):
        mapping = {
            self.STATUS_PENDING: 'warning',
            self.STATUS_APPROVED: 'success',
            self.STATUS_REJECTED: 'danger',
            self.STATUS_WITHDRAWN: 'secondary',
        }
        return mapping.get(self.status, 'secondary')

    def __str__(self):
        return f"Claim #{self.pk} — {self.claimant.username} → {self.item.title} [{self.status}]"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Claim'
        verbose_name_plural = 'Claims'
