from django.conf import settings
from django.db import models

from items.models import Item


class AbuseReport(models.Model):
    REASON_CHOICES = [
        ('SPAM', 'Spam or duplicate'),
        ('INACCURATE', 'False or misleading information'),
        ('INAPPROPRIATE', 'Inappropriate content'),
        ('PRIVACY', 'Personal or sensitive information'),
        ('OTHER', 'Other concern'),
    ]
    STATUS_OPEN = 'OPEN'
    STATUS_REVIEWED = 'REVIEWED'
    STATUS_DISMISSED = 'DISMISSED'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_REVIEWED, 'Reviewed'),
        (STATUS_DISMISSED, 'Dismissed'),
    ]

    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='abuse_reports')
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='abuse_reports')
    reason = models.CharField(max_length=16, choices=REASON_CHOICES)
    details = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_OPEN)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_abuse_reports')
    reviewer_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', '-created_at']
        constraints = [
            models.UniqueConstraint(fields=['item', 'submitted_by'], condition=models.Q(status='OPEN'), name='uniq_open_abuse_report_per_user_item'),
        ]

    def __str__(self):
        return f'{self.get_reason_display()} for item #{self.item_id} ({self.get_status_display()})'
