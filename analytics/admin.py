from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from analytics.models import NoonReportImport, ImportRow


class ImportRowInline(admin.TabularInline):
    model = ImportRow
    extra = 0
    readonly_fields = ('row_number', 'status_badge', 'errors', 'noon_report', 'raw_data')
    fields = ('row_number', 'status_badge', 'errors', 'noon_report')
    can_delete = False
    max_num = 0

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'success': '#059669',
            'error': '#dc2626',
            'skipped': '#d97706',
        }
        color = colors.get(obj.status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )


@admin.register(NoonReportImport)
class NoonReportImportAdmin(admin.ModelAdmin):
    list_display = (
        'original_filename', 'vessel', 'status_badge',
        'total_rows', 'success_count', 'fail_count', 'skip_count',
        'uploaded_by', 'created_at_display',
    )
    list_filter = ('status', 'vessel', 'created_at')
    search_fields = ('original_filename', 'vessel__name')
    readonly_fields = (
        'id', 'file', 'original_filename', 'file_type', 'vessel',
        'status', 'total_rows', 'successful_rows', 'failed_rows',
        'skipped_rows', 'error_summary', 'uploaded_by',
        'created_at', 'completed_at',
    )
    date_hierarchy = 'created_at'
    list_per_page = 30
    list_select_related = ('vessel', 'uploaded_by')
    inlines = [ImportRowInline]

    fieldsets = (
        ('Import Details', {
            'fields': ('original_filename', 'file_type', 'file', 'vessel', 'uploaded_by'),
        }),
        ('Results', {
            'fields': ('status', 'total_rows', 'successful_rows',
                       'failed_rows', 'skipped_rows'),
        }),
        ('Errors', {
            'fields': ('error_summary',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'completed_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Status', ordering='status')
    def status_badge(self, obj):
        colors = {
            'pending': '#94a3b8',
            'processing': '#0284c7',
            'completed': '#059669',
            'completed_with_errors': '#d97706',
            'failed': '#dc2626',
        }
        color = colors.get(obj.status, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display(),
        )

    @admin.display(description='✓ Rows')
    def success_count(self, obj):
        if obj.successful_rows == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="color:#059669;font-weight:600;">{}</span>',
            obj.successful_rows,
        )

    @admin.display(description='✗ Rows')
    def fail_count(self, obj):
        if obj.failed_rows == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="color:#dc2626;font-weight:600;">{}</span>',
            obj.failed_rows,
        )

    @admin.display(description='~ Rows')
    def skip_count(self, obj):
        if obj.skipped_rows == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="color:#d97706;font-weight:600;">{}</span>',
            obj.skipped_rows,
        )

    @admin.display(description='Uploaded', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M'),
            timesince(obj.created_at),
        )
