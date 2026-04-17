"""
Audit logging helper — call from views or admin actions to record audit trail entries.
"""


def log_audit(user, action, target_type, target_id='', target_repr='',
              changes=None, request=None):
    """
    Create an AuditLog entry.

    Args:
        user: The Django User performing the action (or None for system actions).
        action: One of AuditLog.ACTION_CHOICES keys.
        target_type: e.g. 'Document', 'Vessel', 'User'.
        target_id: PK of the affected object.
        target_repr: Human-readable description of the target.
        changes: dict of before/after values.
        request: Django HttpRequest for extracting IP / user-agent.
    """
    from administration.models import AuditLog

    ip_address = None
    user_agent = ''

    if request is not None:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

    AuditLog.objects.create(
        user=user,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        target_repr=str(target_repr)[:300],
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )


def log_system(level, category, message, details=None,
               document=None, session=None, user=None, duration_ms=None):
    """
    Create a SystemLog entry.

    Args:
        level: 'debug', 'info', 'warning', 'error', 'critical'.
        category: One of SystemLog.CATEGORY_CHOICES keys.
        message: Human-readable log message.
        details: Optional dict with extra structured data.
        document: Optional FK to ingestion.Document.
        session: Optional FK to chatbot.ChatSession.
        user: Optional FK to User.
        duration_ms: Optional operation duration in milliseconds.
    """
    from administration.models import SystemLog

    SystemLog.objects.create(
        level=level,
        category=category,
        message=message[:1000],
        details=details or {},
        document=document,
        session=session,
        user=user,
        duration_ms=duration_ms,
    )
