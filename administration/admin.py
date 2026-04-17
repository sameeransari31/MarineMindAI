from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timesince import timesince

from administration.models import (
    UserProfile, Vessel, GuardrailsRule, NoonReport, AnalyticsResult,
    SystemLog, AuditLog, InternetSearchLog, QueryFeedback, SystemConfig,
)

User = get_user_model()


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN SITE BRANDING
# ═════════════════════════════════════════════════════════════════════════════

admin.site.site_header = 'MarineMind'
admin.site.site_title = 'MarineMind Admin'
admin.site.index_title = 'Control Center'
admin.site.site_url = '/'


# ═════════════════════════════════════════════════════════════════════════════
# USER & ACCESS MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = 'MarineMind Profile'
    verbose_name_plural = 'MarineMind Profile'
    fieldsets = (
        ('Role & Permissions', {
            'fields': ('role', 'department', 'can_upload_documents', 'can_query',
                       'can_access_analytics', 'can_access_rag_settings',
                       'can_access_system_settings'),
        }),
        ('Vessel Access', {
            'fields': ('vessel_access',),
            'classes': ('collapse',),
        }),
    )
    filter_horizontal = ('vessel_access',)


# Unregister default User admin, re-register with profile inline
admin.site.unregister(User)


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'get_role', 'is_active_badge', 'is_staff_badge', 'last_login_display',
    )
    list_filter = BaseUserAdmin.list_filter + ('profile__role',)
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 30
    ordering = ('-date_joined',)

    @admin.display(description='Role', ordering='profile__role')
    def get_role(self, obj):
        try:
            role = obj.profile.get_role_display()
            colors = {
                'Administrator': '#dc2626', 'Marine Engineer': '#0284c7',
                'Data Analyst': '#7c3aed', 'Viewer': '#64748b',
            }
            color = colors.get(role, '#64748b')
            return format_html(
                '<span style="background:{};color:#fff;padding:3px 10px;'
                'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
                color, role,
            )
        except UserProfile.DoesNotExist:
            return mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Active', ordering='is_active', boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @admin.display(description='Staff', ordering='is_staff', boolean=True)
    def is_staff_badge(self, obj):
        return obj.is_staff

    @admin.display(description='Last Login', ordering='last_login')
    def last_login_display(self, obj):
        if obj.last_login:
            return format_html(
                '<span title="{}">{} ago</span>',
                obj.last_login.strftime('%Y-%m-%d %H:%M'),
                timesince(obj.last_login),
            )
        return mark_safe('<span style="color:#94a3b8;">Never</span>')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role_badge', 'department', 'upload_perm', 'query_perm',
                    'analytics_perm', 'vessel_count', 'updated_at')
    list_filter = ('role', 'can_upload_documents', 'can_query', 'can_access_analytics')
    search_fields = ('user__username', 'user__email', 'department')
    filter_horizontal = ('vessel_access',)
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 30

    @admin.display(description='Role', ordering='role')
    def role_badge(self, obj):
        colors = {
            'admin': '#dc2626', 'engineer': '#0284c7',
            'analyst': '#7c3aed', 'viewer': '#64748b',
        }
        color = colors.get(obj.role, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_role_display(),
        )

    @admin.display(description='Upload', boolean=True)
    def upload_perm(self, obj):
        return obj.can_upload_documents

    @admin.display(description='Query', boolean=True)
    def query_perm(self, obj):
        return obj.can_query

    @admin.display(description='Analytics', boolean=True)
    def analytics_perm(self, obj):
        return obj.can_access_analytics

    @admin.display(description='Vessels')
    def vessel_count(self, obj):
        count = obj.vessel_access.count()
        if count == 0:
            return mark_safe('<span style="color:#94a3b8;">—</span>')
        return format_html(
            '<span style="background:#e2e5e9;padding:2px 8px;border-radius:8px;'
            'font-size:11px;font-weight:600;">{}</span>', count,
        )


# ═════════════════════════════════════════════════════════════════════════════
# VESSEL MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(Vessel)
class VesselAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'vessel_type_badge', 'imo_number', 'fleet_name',
        'operational_status_badge', 'year_built', 'main_engine_type',
        'document_count', 'noon_report_count',
    )
    list_filter = ('vessel_type', 'operational_status', 'fleet_name', 'flag_state')
    search_fields = ('name', 'imo_number', 'call_sign', 'owner', 'manager')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 25
    ordering = ('name',)
    actions = ['mark_active', 'mark_in_port']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'vessel_type', 'imo_number', 'call_sign',
                       'flag_state', 'classification_society', 'year_built'),
        }),
        ('Tonnage', {
            'fields': ('dwt', 'grt'),
        }),
        ('Engine Details', {
            'fields': ('main_engine_type', 'main_engine_maker',
                       'main_engine_power_kw', 'auxiliary_engine_details',
                       'propeller_type'),
            'classes': ('collapse',),
        }),
        ('Fleet & Ownership', {
            'fields': ('fleet_name', 'owner', 'manager'),
        }),
        ('Status', {
            'fields': ('operational_status', 'notes'),
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Type', ordering='vessel_type')
    def vessel_type_badge(self, obj):
        return format_html(
            '<span style="background:#e2e5e9;color:#334155;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:500;">{}</span>',
            obj.get_vessel_type_display(),
        )

    @admin.display(description='Status', ordering='operational_status')
    def operational_status_badge(self, obj):
        colors = {
            'active': '#059669', 'in_port': '#0284c7',
            'dry_dock': '#d97706', 'laid_up': '#64748b',
            'decommissioned': '#dc2626',
        }
        color = colors.get(obj.operational_status, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_operational_status_display(),
        )

    @admin.display(description='Docs')
    def document_count(self, obj):
        count = obj.documents.count()
        if count == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;'
            'border-radius:8px;font-size:11px;font-weight:600;">{}</span>', count,
        )

    @admin.display(description='Reports')
    def noon_report_count(self, obj):
        count = obj.noon_reports.count()
        if count == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="background:#e0e7ff;color:#4338ca;padding:2px 8px;'
            'border-radius:8px;font-size:11px;font-weight:600;">{}</span>', count,
        )

    @admin.action(description='Mark as Active')
    def mark_active(self, request, queryset):
        updated = queryset.update(operational_status='active')
        self.message_user(request, f"{updated} vessel(s) marked as active.")

    @admin.action(description='Mark as In Port')
    def mark_in_port(self, request, queryset):
        updated = queryset.update(operational_status='in_port')
        self.message_user(request, f"{updated} vessel(s) marked as in port.")


# ═════════════════════════════════════════════════════════════════════════════
# GUARDRAILS & POLICY MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(GuardrailsRule)
class GuardrailsRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'rule_type_badge', 'is_active_badge', 'priority', 'pattern_preview', 'updated_at')
    list_filter = ('rule_type', 'is_active')
    search_fields = ('name', 'pattern', 'description')
    list_editable = ('priority',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 30
    actions = ['activate_rules', 'deactivate_rules']

    fieldsets = (
        (None, {
            'fields': ('name', 'rule_type', 'is_active', 'priority'),
        }),
        ('Pattern & Response', {
            'fields': ('pattern', 'response_message', 'description'),
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Type', ordering='rule_type')
    def rule_type_badge(self, obj):
        colors = {
            'block_category': '#dc2626', 'block_pattern': '#ea580c',
            'allow_pattern': '#059669', 'safety_rule': '#7c3aed',
        }
        color = colors.get(obj.rule_type, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_rule_type_display(),
        )

    @admin.display(description='Active', ordering='is_active')
    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="color:#059669;font-weight:700;">● Active</span>',
            )
        return mark_safe(
            '<span style="color:#dc2626;">● Inactive</span>',
        )

    @admin.display(description='Pattern')
    def pattern_preview(self, obj):
        text = obj.pattern[:60] + ('...' if len(obj.pattern) > 60 else '')
        return format_html(
            '<code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;'
            'font-size:12px;color:#334155;">{}</code>', text,
        )

    @admin.action(description='Activate selected rules')
    def activate_rules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} rule(s) activated.")

    @admin.action(description='Deactivate selected rules')
    def deactivate_rules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} rule(s) deactivated.")


# ═════════════════════════════════════════════════════════════════════════════
# NOON REPORT & PERFORMANCE DATA
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(NoonReport)
class NoonReportAdmin(admin.ModelAdmin):
    list_display = (
        'vessel', 'report_date', 'voyage_number', 'speed_avg', 'fo_consumption',
        'distance_sailed', 'wind_force', 'sea_state', 'cargo_condition',
        'is_validated_badge', 'uploaded_by',
    )
    list_filter = ('vessel', 'is_validated', 'cargo_condition', 'report_date')
    search_fields = ('vessel__name', 'voyage_number', 'remarks',
                     'port_of_departure', 'port_of_arrival')
    date_hierarchy = 'report_date'
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 30
    list_select_related = ('vessel', 'uploaded_by')
    actions = ['validate_reports', 'invalidate_reports']

    fieldsets = (
        ('Report Info', {
            'fields': ('vessel', 'report_date', 'report_time', 'voyage_number'),
        }),
        ('Position', {
            'fields': ('latitude', 'longitude'),
        }),
        ('Voyage', {
            'fields': ('port_of_departure', 'port_of_arrival', 'eta',
                       'distance_sailed', 'distance_to_go',
                       'hours_steaming', 'hours_stopped'),
        }),
        ('Performance', {
            'fields': ('speed_avg', 'speed_ordered', 'rpm_avg', 'slip_percent',
                       'me_load_percent', 'me_power_kw', 'me_exhaust_temp', 'sfoc'),
        }),
        ('Fuel', {
            'fields': ('fo_consumption', 'bf_consumption', 'fo_rob', 'bf_rob',
                       'ae_fo_consumption', 'boiler_fo_consumption'),
        }),
        ('Lube Oil', {
            'fields': ('me_cylinder_oil_consumption', 'me_system_oil_consumption',
                       'ae_lub_oil_consumption'),
            'classes': ('collapse',),
        }),
        ('Draft & Cargo', {
            'fields': ('draft_fore', 'draft_aft', 'draft_mean',
                       'cargo_condition', 'cargo_quantity', 'cargo_type'),
            'classes': ('collapse',),
        }),
        ('Auxiliary & Fresh Water', {
            'fields': ('ae_running_hours', 'fw_consumption', 'fw_produced'),
            'classes': ('collapse',),
        }),
        ('Weather', {
            'fields': ('wind_force', 'wind_direction', 'sea_state',
                       'swell_height', 'current_knots', 'current_direction',
                       'visibility', 'air_temp', 'sea_water_temp', 'barometric_pressure'),
            'classes': ('collapse',),
        }),
        ('Notes & Metadata', {
            'fields': ('remarks', 'is_validated', 'uploaded_by'),
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Validated', ordering='is_validated')
    def is_validated_badge(self, obj):
        if obj.is_validated:
            return mark_safe(
                '<span style="background:#059669;color:#fff;padding:3px 10px;'
                'border-radius:10px;font-size:11px;font-weight:600;">✓ Yes</span>',
            )
        return mark_safe(
            '<span style="background:#f59e0b;color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">✗ No</span>',
        )

    @admin.action(description='Validate selected reports')
    def validate_reports(self, request, queryset):
        updated = queryset.update(is_validated=True)
        self.message_user(request, f"{updated} report(s) validated.")

    @admin.action(description='Mark as not validated')
    def invalidate_reports(self, request, queryset):
        updated = queryset.update(is_validated=False)
        self.message_user(request, f"{updated} report(s) marked as not validated.")


# ═════════════════════════════════════════════════════════════════════════════
# ANALYTICS & GRAPH MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(AnalyticsResult)
class AnalyticsResultAdmin(admin.ModelAdmin):
    list_display = ('title', 'result_type_badge', 'vessel', 'created_by',
                    'created_at_display')
    list_filter = ('result_type', 'vessel', 'created_at')
    search_fields = ('title', 'query_text', 'interpretation')
    readonly_fields = ('id', 'created_at')
    list_per_page = 25
    list_select_related = ('vessel', 'created_by')

    fieldsets = (
        (None, {
            'fields': ('title', 'query_text', 'vessel', 'result_type', 'created_by'),
        }),
        ('Result Data', {
            'fields': ('result_data', 'chart_config', 'interpretation'),
            'classes': ('collapse',),
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Type', ordering='result_type')
    def result_type_badge(self, obj):
        colors = {
            'chart': '#0284c7', 'table': '#059669',
            'summary': '#7c3aed', 'comparison': '#d97706',
        }
        color = colors.get(obj.result_type, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_result_type_display(),
        )

    @admin.display(description='Created', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )


# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM MONITORING & LOGS
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level_badge', 'category_badge', 'message_preview', 'duration_display',
                    'user', 'related_doc', 'created_at_display')
    list_filter = ('level', 'category', 'created_at')
    search_fields = ('message', 'details')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'id', 'level', 'category', 'message', 'details', 'document',
        'session', 'user', 'duration_ms', 'created_at',
    )
    list_per_page = 50
    list_select_related = ('user', 'document')
    actions = ['delete_old_debug_logs']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    @admin.display(description='Level', ordering='level')
    def level_badge(self, obj):
        colors = {
            'debug': '#94a3b8', 'info': '#0284c7',
            'warning': '#d97706', 'error': '#dc2626', 'critical': '#991b1b',
        }
        color = colors.get(obj.level, '#94a3b8')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.level.upper(),
        )

    @admin.display(description='Category', ordering='category')
    def category_badge(self, obj):
        return format_html(
            '<span style="background:#f1f5f9;color:#334155;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:500;">{}</span>',
            obj.get_category_display(),
        )

    @admin.display(description='Message')
    def message_preview(self, obj):
        return obj.message[:100] + ('...' if len(obj.message) > 100 else '')

    @admin.display(description='Duration')
    def duration_display(self, obj):
        if obj.duration_ms is not None:
            if obj.duration_ms >= 1000:
                return format_html(
                    '<span style="color:#d97706;font-weight:600;">{:.1f}s</span>',
                    obj.duration_ms / 1000,
                )
            return f"{obj.duration_ms}ms"
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Document')
    def related_doc(self, obj):
        if obj.document:
            return format_html(
                '<a href="/admin/ingestion/document/{}/change/">{}</a>',
                obj.document.pk,
                str(obj.document.title)[:25],
            )
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Time', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )

    @admin.action(description='Delete debug-level logs')
    def delete_old_debug_logs(self, request, queryset):
        count = queryset.filter(level='debug').delete()[0]
        self.message_user(request, f"{count} debug log(s) deleted.")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user_display', 'action_badge', 'target_type_badge', 'target_repr_short',
                    'ip_address', 'created_at_display')
    list_filter = ('action', 'target_type', 'created_at')
    search_fields = ('target_repr', 'target_id', 'user__username')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'id', 'user', 'action', 'target_type', 'target_id', 'target_repr',
        'changes', 'ip_address', 'user_agent', 'created_at',
    )
    list_per_page = 50
    list_select_related = ('user',)

    fieldsets = (
        ('Action Details', {
            'fields': ('user', 'action', 'target_type', 'target_id', 'target_repr'),
        }),
        ('Changes', {
            'fields': ('changes',),
            'classes': ('collapse',),
        }),
        ('Request Info', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='User')
    def user_display(self, obj):
        if obj.user:
            return obj.user.username
        return mark_safe('<span style="color:#94a3b8;font-style:italic;">System</span>')

    @admin.display(description='Action', ordering='action')
    def action_badge(self, obj):
        colors = {
            'create': '#059669', 'update': '#0284c7', 'delete': '#dc2626',
            'reprocess': '#d97706', 'reindex': '#d97706',
            'login': '#64748b', 'logout': '#64748b',
            'upload': '#059669', 'config_change': '#0284c7',
            'role_change': '#ea580c', 'permission_change': '#ea580c',
        }
        color = colors.get(obj.action, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_action_display(),
        )

    @admin.display(description='Type')
    def target_type_badge(self, obj):
        return format_html(
            '<span style="background:#f1f5f9;color:#334155;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:500;">{}</span>',
            obj.target_type,
        )

    @admin.display(description='Target')
    def target_repr_short(self, obj):
        if obj.target_repr:
            return obj.target_repr[:60] + ('...' if len(obj.target_repr) > 60 else '')
        return obj.target_id or mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Time', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )


# ═════════════════════════════════════════════════════════════════════════════
# INTERNET SEARCH LOGS
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(InternetSearchLog)
class InternetSearchLogAdmin(admin.ModelAdmin):
    list_display = ('query_preview', 'results_count_badge', 'was_successful_badge',
                    'search_duration_display', 'created_at_display')
    list_filter = ('was_successful', 'created_at')
    search_fields = ('query', 'error_message')
    date_hierarchy = 'created_at'
    readonly_fields = (
        'id', 'query', 'results_count', 'domains_used', 'results_summary',
        'triggered_by_message', 'search_duration_ms', 'was_successful',
        'error_message', 'created_at',
    )
    list_per_page = 30

    fieldsets = (
        ('Search Details', {
            'fields': ('query', 'results_count', 'was_successful'),
        }),
        ('Results', {
            'fields': ('domains_used', 'results_summary'),
            'classes': ('collapse',),
        }),
        ('Performance', {
            'fields': ('search_duration_ms', 'triggered_by_message'),
        }),
        ('Errors', {
            'fields': ('error_message',),
            'classes': ('collapse',),
        }),
        ('System', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description='Query')
    def query_preview(self, obj):
        return obj.query[:80] + ('...' if len(obj.query) > 80 else '')

    @admin.display(description='Results')
    def results_count_badge(self, obj):
        if obj.results_count == 0:
            return mark_safe('<span style="color:#94a3b8;">0</span>')
        return format_html(
            '<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;'
            'border-radius:8px;font-size:11px;font-weight:600;">{}</span>',
            obj.results_count,
        )

    @admin.display(description='Success', ordering='was_successful')
    def was_successful_badge(self, obj):
        if obj.was_successful:
            return mark_safe(
                '<span style="background:#059669;color:#fff;padding:3px 10px;'
                'border-radius:10px;font-size:11px;font-weight:600;">✓ Yes</span>',
            )
        return mark_safe(
            '<span style="background:#dc2626;color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">✗ Failed</span>',
        )

    @admin.display(description='Duration')
    def search_duration_display(self, obj):
        if obj.search_duration_ms is not None:
            if obj.search_duration_ms >= 1000:
                return format_html(
                    '<span style="color:#d97706;font-weight:600;">{:.1f}s</span>',
                    obj.search_duration_ms / 1000,
                )
            return f"{obj.search_duration_ms}ms"
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    @admin.display(description='Time', ordering='created_at')
    def created_at_display(self, obj):
        return format_html(
            '<span title="{}" style="white-space:nowrap;">{} ago</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            timesince(obj.created_at),
        )


# ═════════════════════════════════════════════════════════════════════════════
# FEEDBACK & EVALUATION
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(QueryFeedback)
class QueryFeedbackAdmin(admin.ModelAdmin):
    list_display = ('message_preview', 'rating_badge', 'retrieval_quality_display',
                    'reviewed_by', 'created_at')
    list_filter = ('rating', 'retrieval_quality', 'created_at')
    search_fields = ('admin_notes', 'suggested_answer', 'message__content')
    readonly_fields = ('id', 'created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Response Under Review', {
            'fields': ('message',),
        }),
        ('Evaluation', {
            'fields': ('rating', 'retrieval_quality', 'admin_notes', 'suggested_answer'),
        }),
        ('Reviewer', {
            'fields': ('reviewed_by',),
        }),
        ('System', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Answer')
    def message_preview(self, obj):
        return obj.message.content[:80] + ('...' if len(obj.message.content) > 80 else '')

    @admin.display(description='Rating', ordering='rating')
    def rating_badge(self, obj):
        colors = {
            'correct': '#059669', 'incorrect': '#dc2626',
            'partial': '#d97706', 'needs_improvement': '#ea580c',
        }
        color = colors.get(obj.rating, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_rating_display(),
        )

    @admin.display(description='Retrieval')
    def retrieval_quality_display(self, obj):
        if obj.retrieval_quality:
            return obj.get_retrieval_quality_display()
        return '—'


# ═════════════════════════════════════════════════════════════════════════════
# SETTINGS & CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key_display', 'category_badge', 'value_preview', 'value_type',
                    'is_sensitive_badge', 'updated_by', 'updated_at')
    list_filter = ('category', 'value_type', 'is_sensitive')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)
    list_per_page = 30

    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'value_type', 'category'),
        }),
        ('Details', {
            'fields': ('description', 'is_sensitive', 'updated_by', 'updated_at'),
        }),
    )

    @admin.display(description='Key', ordering='key')
    def key_display(self, obj):
        return format_html(
            '<code style="background:#f1f5f9;padding:3px 8px;border-radius:4px;'
            'font-size:12px;color:#334155;font-weight:600;">{}</code>', obj.key,
        )

    @admin.display(description='Category', ordering='category')
    def category_badge(self, obj):
        colors = {
            'model': '#7c3aed', 'embedding': '#0284c7', 'chunking': '#059669',
            'retrieval': '#d97706', 'reranking': '#ea580c', 'guardrails': '#dc2626',
            'search': '#0d9488', 'general': '#64748b',
        }
        color = colors.get(obj.category, '#64748b')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_category_display(),
        )

    @admin.display(description='Value')
    def value_preview(self, obj):
        if obj.is_sensitive:
            return mark_safe(
                '<span style="color:#94a3b8;letter-spacing:2px;">••••••••</span>',
            )
        val = obj.value
        text = val[:50] + ('...' if len(val) > 50 else '')
        return format_html(
            '<code style="background:#f8fafc;padding:2px 6px;border-radius:3px;'
            'font-size:12px;">{}</code>', text,
        )

    @admin.display(description='🔒', ordering='is_sensitive')
    def is_sensitive_badge(self, obj):
        if obj.is_sensitive:
            return mark_safe(
                '<span style="color:#dc2626;font-size:14px;" title="Sensitive">🔒</span>',
            )
        return mark_safe('<span style="color:#94a3b8;">—</span>')

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
