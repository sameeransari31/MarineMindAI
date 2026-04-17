import uuid
from django.db import models
from django.conf import settings


class NoonReportImport(models.Model):
    """Tracks a single CSV/Excel file upload for noon report data."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('completed_with_errors', 'Completed with Errors'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to='uploads/noon_report_imports/')
    original_filename = models.CharField(max_length=500)
    file_type = models.CharField(max_length=10, help_text='csv or xlsx')
    vessel = models.ForeignKey(
        'administration.Vessel', on_delete=models.CASCADE,
        related_name='noon_report_imports',
        help_text='Target vessel for this import',
    )

    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='pending')
    total_rows = models.PositiveIntegerField(default=0)
    successful_rows = models.PositiveIntegerField(default=0)
    failed_rows = models.PositiveIntegerField(default=0)
    skipped_rows = models.PositiveIntegerField(default=0)
    error_summary = models.JSONField(default=list, blank=True, help_text='List of error messages per row')

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='noon_report_imports',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Noon Report Import'
        verbose_name_plural = 'Noon Report Imports'

    def __str__(self):
        return f"{self.original_filename} → {self.vessel.name} ({self.get_status_display()})"


class ImportRow(models.Model):
    """Tracks the result of importing each individual row from a file."""

    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    import_job = models.ForeignKey(
        NoonReportImport, on_delete=models.CASCADE, related_name='rows',
    )
    row_number = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    raw_data = models.JSONField(default=dict, help_text='Original row data from the file')
    errors = models.JSONField(default=list, blank=True, help_text='Validation errors for this row')
    noon_report = models.ForeignKey(
        'administration.NoonReport', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='import_rows',
        help_text='The NoonReport created from this row (if successful)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number']
        unique_together = ['import_job', 'row_number']
        verbose_name = 'Import Row'
        verbose_name_plural = 'Import Rows'

    def __str__(self):
        return f"Row {self.row_number} — {self.get_status_display()}"
