from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from dashboard.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('severity_badge', 'alert_type_badge', 'title', 'vessel',
                    'is_read_badge', 'created_at_display')
    list_filter = ('severity', 'alert_type', 'is_read', 'vessel', 'created_at')
    search_fields = ('title', 'message', 'vessel__name')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at')
    list_per_page = 30
    list_select_related = ('vessel',)
    actions = ['mark_as_read', 'mark_as_unread']

    fieldsets = (
        ('Alert Info', {
            'fields': ('alert_type', 'severity', 'title', 'message', 'vessel'),
        }),
        ('Details', {
            'fields': ('details',),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': ('is_read',),
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Severity', ordering='severity')
    def severity_badge(self, obj):
        colors = {
            'info': '#0284c7', 'warning': '#d97706',
            'error': '#dc2626', 'critical': '#991b1b',
        }
        color = colors.get(obj.severity, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_severity_display(),
        )

    @admin.display(description='Type', ordering='alert_type')
    def alert_type_badge(self, obj):
        return format_html(
            '<span style="background:#f1f5f9;color:#334155;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:500;">{}</span>',
            obj.get_alert_type_display(),
        )

    @admin.display(description='Read', ordering='is_read')
    def is_read_badge(self, obj):
        if obj.is_read:
            return mark_safe(
                '<span style="color:#94a3b8;">Read</span>',
            )
        return mark_safe(
            '<span style="background:#dc2626;color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">New</span>',
        )

    @admin.display(description='Time', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )

    @admin.action(description='Mark as read')
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} alert(s) marked as read.")

    @admin.action(description='Mark as unread')
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} alert(s) marked as unread.")
