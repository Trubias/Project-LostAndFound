from django.db import models


class ApiTestRun(models.Model):
    STATUS_RUNNING = 'running'
    STATUS_PASSED = 'passed'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_RUNNING, 'Running'),
        (STATUS_PASSED, 'Passed'),
        (STATUS_FAILED, 'Failed'),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_RUNNING)
    requested_by = models.CharField(max_length=150)
    endpoint_id = models.CharField(max_length=512, blank=True)
    http_method = models.CharField(max_length=10, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    passed_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    results = models.JSONField(default=list)
    output = models.TextField(blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'API test {self.pk}: {self.status}'
