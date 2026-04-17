import uuid
from django.db import models
from django.conf import settings


class Document(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    DOCUMENT_TYPE_CHOICES = [
        ('manual', 'Ship Manual'),
        ('sop', 'Standard Operating Procedure'),
        ('report', 'Technical Report'),
        ('noon_report', 'Noon Report'),
        ('drawing', 'Technical Drawing'),
        ('certificate', 'Certificate'),
        ('checklist', 'Checklist'),
        ('circular', 'Circular / Notice'),
        ('other', 'Other'),
    ]

    EMBEDDING_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    file = models.FileField(upload_to='uploads/documents/')
    file_type = models.CharField(max_length=20, blank=True)
    file_size = models.PositiveIntegerField(default=0)
    total_pages = models.PositiveIntegerField(null=True, blank=True)
    total_chunks = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # New fields for admin panel
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='other')
    vessel = models.ForeignKey(
        'administration.Vessel', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='documents',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='uploaded_documents',
    )
    version = models.PositiveIntegerField(default=1)
    previous_version = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='next_versions',
    )
    embedding_status = models.CharField(
        max_length=20, choices=EMBEDDING_STATUS_CHOICES, default='not_started',
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} ({self.status})"
