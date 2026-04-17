from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince
from chatbot.models import ChatSession, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('id', 'role_display', 'content_short', 'agent_used', 'route',
                       'processing_time', 'created_at')
    fields = ('role_display', 'content_short', 'agent_used', 'route', 'processing_time', 'created_at')
    show_change_link = True
    max_num = 0

    @admin.display(description='Role')
    def role_display(self, obj):
        colors = {'user': '#0284c7', 'assistant': '#059669', 'system': '#64748b'}
        color = colors.get(obj.role, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:8px;font-size:10px;font-weight:600;">{}</span>',
            color, obj.role.upper(),
        )

    @admin.display(description='Content')
    def content_short(self, obj):
        return obj.content[:80] + ('...' if len(obj.content) > 80 else '')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'message_count', 'created_at_display', 'updated_at_display')
    list_filter = ('created_at', 'updated_at', 'user')
    search_fields = ('title', 'user__username', 'user__email')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [ChatMessageInline]
    list_per_page = 30
    list_select_related = ('user',)

    @admin.display(description='Messages')
    def message_count(self, obj):
        count = obj.messages.count()
        if count == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;'
            'border-radius:8px;font-size:11px;font-weight:600;">{}</span>', count,
        )

    @admin.display(description='Created', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M'),
            timesince(obj.created_at),
        )

    @admin.display(description='Last Active', ordering='updated_at')
    def updated_at_display(self, obj):
        return format_html(
            '<span title="{}">{} ago</span>',
            obj.updated_at.strftime('%Y-%m-%d %H:%M'),
            timesince(obj.updated_at),
        )


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('role_badge', 'content_preview', 'agent_badge', 'route_badge',
                    'feedback_badge', 'processing_time_display', 'session_link',
                    'created_at_display')
    list_filter = ('role', 'agent_used', 'route', 'feedback', 'created_at')
    search_fields = ('content', 'session__title')
    date_hierarchy = 'created_at'
    readonly_fields = ('id', 'session', 'role', 'content', 'agent_used', 'route',
                       'sources', 'citation_map', 'graph', 'diagnosis',
                       'processing_time', 'created_at')
    list_per_page = 50

    fieldsets = (
        ('Message', {
            'fields': ('session', 'role', 'content'),
        }),
        ('Pipeline Info', {
            'fields': ('agent_used', 'route', 'processing_time'),
        }),
        ('AI Outputs', {
            'fields': ('graph', 'diagnosis'),
            'classes': ('collapse',),
        }),
        ('Sources & Citations', {
            'fields': ('sources', 'citation_map'),
            'classes': ('collapse',),
        }),
        ('Feedback', {
            'fields': ('feedback', 'feedback_note'),
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        colors = {'user': '#0284c7', 'assistant': '#059669', 'system': '#64748b'}
        color = colors.get(obj.role, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.role.capitalize(),
        )

    @admin.display(description='Agent')
    def agent_badge(self, obj):
        if not obj.agent_used:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        colors = {
            'rag': '#0284c7', 'internet': '#ea580c', 'hybrid': '#7c3aed',
            'guardrails': '#dc2626', 'graph': '#0d9488', 'diagnosis': '#d97706',
        }
        color = colors.get(obj.agent_used, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.agent_used,
        )

    @admin.display(description='Route')
    def route_badge(self, obj):
        if not obj.route:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        colors = {
            'rag': '#0284c7', 'internet': '#ea580c', 'hybrid': '#7c3aed',
            'greeting': '#059669', 'rejected': '#dc2626',
            'graph': '#0d9488', 'diagnosis': '#d97706',
        }
        color = colors.get(obj.route, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.route,
        )

    @admin.display(description='Feedback')
    def feedback_badge(self, obj):
        if not obj.feedback:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        colors = {
            'correct': '#059669', 'incorrect': '#dc2626', 'partial': '#d97706',
        }
        color = colors.get(obj.feedback, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_feedback_display(),
        )

    @admin.display(description='Time')
    def processing_time_display(self, obj):
        if obj.processing_time is not None:
            formatted = f"{obj.processing_time:.1f}s"
            if obj.processing_time >= 5:
                return format_html(
                    '<span style="color:#dc2626;font-weight:600;">{}</span>',
                    formatted,
                )
            elif obj.processing_time >= 2:
                return format_html(
                    '<span style="color:#d97706;font-weight:600;">{}</span>',
                    formatted,
                )
            return formatted
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Content')
    def content_preview(self, obj):
        return obj.content[:100] + ('...' if len(obj.content) > 100 else '')

    @admin.display(description='Session')
    def session_link(self, obj):
        return format_html(
            '<a href="/admin/chatbot/chatsession/{}/change/">{}</a>',
            obj.session.pk,
            obj.session.title[:25],
        )

    @admin.display(description='Time', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )
