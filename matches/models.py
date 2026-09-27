from django.db import models
from items.models import Item


class ItemMatch(models.Model):
    """
    A possible match between a Lost item and a Found item.

    Matches are generated automatically when a new ACTIVE Lost or Found item
    is created.  Only pairs with a score >= settings.MATCH_THRESHOLD are stored.

    Status:
        PENDING   — match detected, awaiting user review
        CONFIRMED — at least one reporter agreed this is the same item
        DISMISSED — the match was explicitly rejected by a reporter

    Constraints:
        • lost_item.item_type must always be LOST
        • found_item.item_type must always be FOUND
        • The (lost_item, found_item) pair is unique — no duplicate matches
    """

    STATUS_PENDING   = 'PENDING'
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_DISMISSED = 'DISMISSED'

    STATUS_CHOICES = [
        (STATUS_PENDING,   'Pending'),
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_DISMISSED, 'Dismissed'),
    ]

    # ── Relationships ─────────────────────────────────────────────
    lost_item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='lost_matches',
        help_text='Must have item_type=LOST.',
    )
    found_item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name='found_matches',
        help_text='Must have item_type=FOUND.',
    )

    # ── Match data ────────────────────────────────────────────────
    score = models.PositiveSmallIntegerField(
        help_text='Match quality 0–100 (see matches.engine for scoring rules).',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # ── Score breakdown (stored for the detail page) ──────────────
    score_category    = models.PositiveSmallIntegerField(default=0)
    score_location    = models.PositiveSmallIntegerField(default=0)
    score_title       = models.PositiveSmallIntegerField(default=0)
    score_description = models.PositiveSmallIntegerField(default=0)
    score_date        = models.PositiveSmallIntegerField(default=0)

    # ── Timestamps ────────────────────────────────────────────────
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # ── Helpers ───────────────────────────────────────────────────
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def is_confirmed(self):
        return self.status == self.STATUS_CONFIRMED

    def is_dismissed(self):
        return self.status == self.STATUS_DISMISSED

    def involves_user(self, user):
        """True if *user* reported either the lost or found item."""
        return (
            self.lost_item.reporter_id == user.pk
            or self.found_item.reporter_id == user.pk
        )

    def __str__(self):
        return (
            f"Match #{self.pk} — "
            f"[LOST] {self.lost_item.title} ↔ "
            f"[FOUND] {self.found_item.title} "
            f"(score={self.score}, {self.status})"
        )

    class Meta:
        ordering = ['-score', '-created_at']
        verbose_name = 'Item Match'
        verbose_name_plural = 'Item Matches'
        # One match record per Lost/Found pair.
        unique_together = [('lost_item', 'found_item')]
