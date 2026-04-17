import uuid
from django.db import models


class Alert(models.Model):
    """System-generated alerts for abnormal conditions and failures."""

    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    ALERT_TYPE_CHOICES = [
        ('performance', 'Performance Anomaly'),
        ('system', 'System Failure'),
        ('ingestion', 'Ingestion Issue'),
        ('fuel', 'Abnormal Fuel Usage'),
        ('query', 'Query Failure'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='warning')
    title = models.CharField(max_length=300)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    vessel = models.ForeignKey(
        'administration.Vessel', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alerts',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Alert'
        verbose_name_plural = 'Alerts'
        indexes = [
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"
