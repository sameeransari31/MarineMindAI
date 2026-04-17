import threading
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from ingestion.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'document_type_badge', 'vessel', 'file_type_badge', 'file_size_display',
        'status_badge', 'embedding_status_badge', 'total_pages', 'total_chunks',
        'version', 'uploaded_by', 'uploaded_at_display',
    )
    list_filter = ('status', 'embedding_status', 'document_type', 'file_type',
                   'vessel', 'uploaded_at')
    search_fields = ('title', 'description', 'vessel__name', 'uploaded_by__username')
    date_hierarchy = 'uploaded_at'
    readonly_fields = ('id', 'total_chunks', 'total_pages', 'file_size',
                       'processed_at', 'uploaded_at')
    list_per_page = 30
    list_select_related = ('vessel', 'uploaded_by')
    actions = ['reprocess_documents', 'mark_as_pending']

    fieldsets = (
        ('Document Info', {
            'fields': ('title', 'description', 'document_type', 'file', 'version',
                       'previous_version'),
        }),
        ('Vessel Association', {
            'fields': ('vessel',),
        }),
        ('Processing Status', {
            'fields': ('status', 'embedding_status', 'error_message'),
        }),
        ('File Metadata', {
            'fields': ('file_type', 'file_size', 'total_pages', 'total_chunks'),
        }),
        ('Tracking', {
            'fields': ('uploaded_by', 'uploaded_at', 'processed_at'),
        }),
        ('System', {
            'fields': ('id',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Type', ordering='document_type')
    def document_type_badge(self, obj):
        colors = {
            'manual': '#0284c7', 'sop': '#7c3aed', 'report': '#059669',
            'noon_report': '#d97706', 'drawing': '#64748b', 'certificate': '#0d9488',
            'checklist': '#ea580c', 'circular': '#dc2626', 'other': '#94a3b8',
        }
        color = colors.get(obj.document_type, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_document_type_display(),
        )

    @admin.display(description='Format')
    def file_type_badge(self, obj):
        if not obj.file_type:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        colors = {
            'pdf': '#dc2626', 'docx': '#0284c7', 'doc': '#0284c7',
            'xlsx': '#059669', 'xls': '#059669', 'csv': '#059669',
            'txt': '#64748b', 'pptx': '#d97706',
        }
        ft = obj.file_type.lower()
        color = colors.get(ft, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;">{}</span>',
            color, ft,
        )

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending': '#d97706', 'processing': '#0284c7',
            'completed': '#059669', 'failed': '#dc2626',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description='Embeddings', ordering='embedding_status')
    def embedding_status_badge(self, obj):
        colors = {
            'not_started': '#94a3b8', 'in_progress': '#0284c7',
            'completed': '#059669', 'failed': '#dc2626',
        }
        color = colors.get(obj.embedding_status, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_embedding_status_display(),
        )

    @admin.display(description='Size')
    def file_size_display(self, obj):
        if obj.file_size >= 1024 * 1024:
            return f"{obj.file_size / (1024 * 1024):.1f} MB"
        elif obj.file_size >= 1024:
            return f"{obj.file_size / 1024:.0f} KB"
        return f"{obj.file_size} B"

    @admin.display(description='Uploaded', ordering='uploaded_at')
    def uploaded_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            timesince(obj.uploaded_at),
        )

    @admin.action(description='Reprocess selected documents')
    def reprocess_documents(self, request, queryset):
        from ingestion.services import process_document
        count = 0
        for doc in queryset:
            doc.status = 'pending'
            doc.error_message = ''
            doc.save(update_fields=['status', 'error_message'])
            thread = threading.Thread(target=process_document, args=(doc,), daemon=True)
            thread.start()
            count += 1
        self.message_user(request, f"{count} document(s) queued for reprocessing.")

    @admin.action(description='Mark selected as pending')
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending', error_message='')
        self.message_user(request, f"{updated} document(s) marked as pending.")

    def save_model(self, request, obj, form, change):
        if not change and not obj.uploaded_by:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
