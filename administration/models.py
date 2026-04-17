import uuid
from django.db import models
from django.conf import settings


# ─────────────────────────────────────────────────────────────────────────────
# USER & ACCESS MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class UserProfile(models.Model):
    """Extended user profile with role-based access control for MarineMind."""

    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('engineer', 'Marine Engineer'),
        ('analyst', 'Data Analyst'),
        ('viewer', 'Viewer'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.CharField(max_length=100, blank=True)
    can_upload_documents = models.BooleanField(default=False)
    can_query = models.BooleanField(default=True)
    can_access_analytics = models.BooleanField(default=False)
    can_access_rag_settings = models.BooleanField(default=False)
    can_access_system_settings = models.BooleanField(default=False)
    vessel_access = models.ManyToManyField('Vessel', blank=True, related_name='authorized_users')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} — {self.get_role_display()}"


# ─────────────────────────────────────────────────────────────────────────────
# VESSEL MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class Vessel(models.Model):
    """Vessel/ship with operational details, engine info, and fleet grouping."""

    VESSEL_TYPE_CHOICES = [
        ('bulk_carrier', 'Bulk Carrier'),
        ('tanker', 'Tanker'),
        ('container', 'Container Ship'),
        ('lng_carrier', 'LNG Carrier'),
        ('lpg_carrier', 'LPG Carrier'),
        ('general_cargo', 'General Cargo'),
        ('ro_ro', 'Ro-Ro'),
        ('passenger', 'Passenger Ship'),
        ('offshore', 'Offshore Vessel'),
        ('tug', 'Tug'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('in_port', 'In Port'),
        ('dry_dock', 'Dry Dock'),
        ('laid_up', 'Laid Up'),
        ('decommissioned', 'Decommissioned'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    vessel_type = models.CharField(max_length=30, choices=VESSEL_TYPE_CHOICES)
    imo_number = models.CharField(max_length=20, unique=True, help_text='IMO vessel identification number')
    call_sign = models.CharField(max_length=20, blank=True)
    flag_state = models.CharField(max_length=100, blank=True)
    classification_society = models.CharField(max_length=100, blank=True)
    year_built = models.PositiveIntegerField(null=True, blank=True)
    dwt = models.PositiveIntegerField(null=True, blank=True, help_text='Deadweight Tonnage')
    grt = models.PositiveIntegerField(null=True, blank=True, help_text='Gross Registered Tonnage')

    # Engine details
    main_engine_type = models.CharField(max_length=255, blank=True, help_text='e.g. MAN B&W 6S50MC-C')
    main_engine_maker = models.CharField(max_length=255, blank=True)
    main_engine_power_kw = models.PositiveIntegerField(null=True, blank=True, help_text='Main engine MCR in kW')
    auxiliary_engine_details = models.TextField(blank=True)
    propeller_type = models.CharField(max_length=100, blank=True)

    # Fleet grouping
    fleet_name = models.CharField(max_length=100, blank=True, help_text='Fleet or pool grouping')
    owner = models.CharField(max_length=255, blank=True)
    manager = models.CharField(max_length=255, blank=True)

    # Status
    operational_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Vessel'
        verbose_name_plural = 'Vessels'

    def __str__(self):
        return f"{self.name} (IMO: {self.imo_number})"


# ─────────────────────────────────────────────────────────────────────────────
# GUARDRAILS & POLICY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class GuardrailsRule(models.Model):
    """Configurable rules for the guardrails agent — blocked categories, patterns."""

    RULE_TYPE_CHOICES = [
        ('block_category', 'Block Category'),
        ('block_pattern', 'Block Pattern'),
        ('allow_pattern', 'Allow Pattern'),
        ('safety_rule', 'Safety Rule'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)
    pattern = models.TextField(help_text='Regex pattern or keywords to match against queries')
    response_message = models.TextField(
        blank=True,
        help_text='Custom rejection message. Leave blank for default.',
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=0, help_text='Higher = evaluated first')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'name']
        verbose_name = 'Guardrails Rule'
        verbose_name_plural = 'Guardrails Rules'

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"[{status}] {self.name} ({self.get_rule_type_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# NOON REPORT & PERFORMANCE DATA
# ─────────────────────────────────────────────────────────────────────────────

class NoonReport(models.Model):
    """Structured noon report data for vessel performance analysis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vessel = models.ForeignKey(Vessel, on_delete=models.CASCADE, related_name='noon_reports')
    report_date = models.DateField()
    report_time = models.TimeField(default='12:00:00')

    # Position
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Voyage
    voyage_number = models.CharField(max_length=50, blank=True)
    port_of_departure = models.CharField(max_length=100, blank=True)
    port_of_arrival = models.CharField(max_length=100, blank=True)
    eta = models.DateTimeField(null=True, blank=True)

    # Performance
    speed_avg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Average speed in knots')
    speed_ordered = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    distance_sailed = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text='Distance in nautical miles')
    distance_to_go = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    rpm_avg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    slip_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    # Fuel consumption (metric tonnes)
    fo_consumption = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text='Fuel Oil consumption (MT)')
    bf_consumption = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text='Bio Fuel consumption (MT)')
    fo_rob = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='Fuel Oil Remaining on Board (MT)')
    bf_rob = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text='Bio Fuel Remaining on Board (MT)')

    # Main engine
    me_load_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    me_power_kw = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True, help_text='Main engine power output (kW)')
    me_exhaust_temp = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text='°C')
    sfoc = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='Specific Fuel Oil Consumption (g/kWh)')

    # Lube oil consumption (litres)
    me_cylinder_oil_consumption = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='ME cylinder oil consumption (litres)')
    me_system_oil_consumption = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='ME system oil consumption (litres)')
    ae_lub_oil_consumption = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='AE lube oil consumption (litres)')

    # Draft (metres)
    draft_fore = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Forward draft (metres)')
    draft_aft = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Aft draft (metres)')
    draft_mean = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Mean draft (metres)')

    # Cargo
    CARGO_CONDITION_CHOICES = [
        ('laden', 'Laden'),
        ('ballast', 'Ballast'),
        ('part_laden', 'Part Laden'),
    ]
    cargo_condition = models.CharField(max_length=15, choices=CARGO_CONDITION_CHOICES, blank=True)
    cargo_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Cargo quantity (MT)')
    cargo_type = models.CharField(max_length=100, blank=True)

    # Auxiliary engine
    ae_running_hours = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text='Total AE running hours for the day')
    ae_fo_consumption = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text='AE Fuel Oil consumption (MT)')
    boiler_fo_consumption = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True, help_text='Boiler FO consumption (MT)')

    # Fresh water
    fw_consumption = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='Fresh water consumption (MT)')
    fw_produced = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text='Fresh water produced (MT)')

    # Weather
    wind_force = models.PositiveIntegerField(null=True, blank=True, help_text='Beaufort scale 0-12')
    wind_direction = models.CharField(max_length=10, blank=True)
    sea_state = models.PositiveIntegerField(null=True, blank=True, help_text='Douglas sea scale 0-9')
    swell_height = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='metres')
    current_knots = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    current_direction = models.CharField(max_length=10, blank=True)
    visibility = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='Visibility in nautical miles')
    air_temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='Air temperature (°C)')
    sea_water_temp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text='Sea water temperature (°C)')
    barometric_pressure = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True, help_text='Barometric pressure (mbar)')

    # Steaming hours
    hours_steaming = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Hours steaming since last report')
    hours_stopped = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text='Hours stopped since last report')

    # Notes
    remarks = models.TextField(blank=True)

    # Metadata
    is_validated = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='noon_reports_uploaded',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-report_date', '-report_time']
        unique_together = ['vessel', 'report_date', 'report_time']
        verbose_name = 'Noon Report'
        verbose_name_plural = 'Noon Reports'

    def __str__(self):
        return f"{self.vessel.name} — {self.report_date}"


# ─────────────────────────────────────────────────────────────────────────────
# ANALYTICS & GRAPH MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

class AnalyticsResult(models.Model):
    """Stored analytics outputs — charts, graphs, performance summaries."""

    RESULT_TYPE_CHOICES = [
        ('chart', 'Chart/Graph'),
        ('table', 'Table'),
        ('summary', 'Summary Report'),
        ('comparison', 'Comparison'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    query_text = models.TextField(help_text='Natural language query that generated this result')
    vessel = models.ForeignKey(
        Vessel, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='analytics_results',
    )
    result_type = models.CharField(max_length=20, choices=RESULT_TYPE_CHOICES)
    result_data = models.JSONField(default=dict, blank=True, help_text='Structured data for the result')
    chart_config = models.JSONField(default=dict, blank=True, help_text='Chart.js / plotting configuration')
    interpretation = models.TextField(blank=True, help_text='AI-generated interpretation of the result')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='analytics_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analytics Result'
        verbose_name_plural = 'Analytics Results'

    def __str__(self):
        return f"{self.title} ({self.get_result_type_display()})"


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM MONITORING & LOGS
# ─────────────────────────────────────────────────────────────────────────────

class SystemLog(models.Model):
    """Centralised log for ingestion, indexing, query pipeline, and system events."""

    LEVEL_CHOICES = [
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]

    CATEGORY_CHOICES = [
        ('ingestion', 'Document Ingestion'),
        ('indexing', 'Vector Indexing'),
        ('query_pipeline', 'Query Pipeline'),
        ('guardrails', 'Guardrails'),
        ('routing', 'Query Routing'),
        ('rag', 'RAG Retrieval'),
        ('search', 'Internet Search'),
        ('reranking', 'Reranking'),
        ('llm', 'LLM Generation'),
        ('auth', 'Authentication'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    document = models.ForeignKey(
        'ingestion.Document', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='system_logs',
    )
    session = models.ForeignKey(
        'chatbot.ChatSession', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='system_logs',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='system_logs',
    )
    duration_ms = models.PositiveIntegerField(null=True, blank=True, help_text='Operation duration in ms')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
        indexes = [
            models.Index(fields=['category', '-created_at']),
            models.Index(fields=['level', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.level.upper()}] [{self.category}] {self.message[:80]}"


class AuditLog(models.Model):
    """Immutable audit trail for administrative actions."""

    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('reprocess', 'Reprocess'),
        ('reindex', 'Re-index'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('upload', 'Upload'),
        ('download', 'Download'),
        ('config_change', 'Config Change'),
        ('role_change', 'Role Change'),
        ('permission_change', 'Permission Change'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_type = models.CharField(max_length=50, help_text='Model/entity type affected')
    target_id = models.CharField(max_length=100, blank=True)
    target_repr = models.CharField(max_length=300, blank=True, help_text='Human-readable target description')
    changes = models.JSONField(default=dict, blank=True, help_text='Before/after snapshot of changed fields')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['action', '-created_at']),
            models.Index(fields=['target_type', '-created_at']),
        ]

    def __str__(self):
        user_str = self.user.username if self.user else 'System'
        return f"{user_str} — {self.get_action_display()} — {self.target_type}"


# ─────────────────────────────────────────────────────────────────────────────
# INTERNET SEARCH CONFIGURATION & LOGS
# ─────────────────────────────────────────────────────────────────────────────

class InternetSearchLog(models.Model):
    """Tracks internet search usage for monitoring and debugging."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    query = models.TextField()
    results_count = models.PositiveIntegerField(default=0)
    domains_used = models.JSONField(default=list, blank=True)
    results_summary = models.JSONField(default=list, blank=True, help_text='Title+URL of each result')
    triggered_by_message = models.ForeignKey(
        'chatbot.ChatMessage', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='search_logs',
    )
    search_duration_ms = models.PositiveIntegerField(null=True, blank=True)
    was_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Internet Search Log'
        verbose_name_plural = 'Internet Search Logs'

    def __str__(self):
        return f"Search: {self.query[:60]} ({self.results_count} results)"


# ─────────────────────────────────────────────────────────────────────────────
# FEEDBACK & EVALUATION
# ─────────────────────────────────────────────────────────────────────────────

class QueryFeedback(models.Model):
    """Admin evaluation/feedback on AI responses for quality improvement."""

    RATING_CHOICES = [
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect'),
        ('partial', 'Partially Correct'),
        ('needs_improvement', 'Needs Improvement'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        'chatbot.ChatMessage', on_delete=models.CASCADE,
        related_name='feedbacks',
    )
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    retrieval_quality = models.CharField(
        max_length=20, choices=RATING_CHOICES, blank=True,
        help_text='Quality of retrieved source documents',
    )
    admin_notes = models.TextField(blank=True)
    suggested_answer = models.TextField(blank=True, help_text='What the correct answer should have been')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='feedbacks_given',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Query Feedback'
        verbose_name_plural = 'Query Feedbacks'

    def __str__(self):
        return f"Feedback: {self.get_rating_display()} — {self.message.content[:50]}"


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS & CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

class SystemConfig(models.Model):
    """Runtime-editable system configuration (non-sensitive settings only)."""

    VALUE_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
    ]

    CATEGORY_CHOICES = [
        ('model', 'LLM Model Settings'),
        ('embedding', 'Embedding Settings'),
        ('chunking', 'Chunking Settings'),
        ('retrieval', 'Retrieval Settings'),
        ('reranking', 'Reranking Settings'),
        ('guardrails', 'Guardrails Settings'),
        ('search', 'Internet Search Settings'),
        ('general', 'General Settings'),
    ]

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    value_type = models.CharField(max_length=10, choices=VALUE_TYPE_CHOICES, default='string')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    description = models.TextField(blank=True)
    is_sensitive = models.BooleanField(
        default=False,
        help_text='Sensitive values (API keys) should be in .env, not here.',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'key']
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'

    def __str__(self):
        return f"[{self.get_category_display()}] {self.key}"

    def get_typed_value(self):
        """Return the value cast to the correct Python type."""
        import json as _json
        if self.value_type == 'integer':
            return int(self.value)
        elif self.value_type == 'float':
            return float(self.value)
        elif self.value_type == 'boolean':
            return self.value.lower() in ('true', '1', 'yes')
        elif self.value_type == 'json':
            return _json.loads(self.value)
        return self.value
