import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile when a new User is created."""
    from administration.models import UserProfile

    if created:
        role = 'admin' if instance.is_superuser else 'viewer'
        UserProfile.objects.create(
            user=instance,
            role=role,
            can_upload_documents=instance.is_superuser or instance.is_staff,
            can_query=True,
            can_access_analytics=instance.is_superuser or instance.is_staff,
            can_access_rag_settings=instance.is_superuser,
            can_access_system_settings=instance.is_superuser,
        )


@receiver(post_save, sender='administration.NoonReport')
def check_noon_report_anomalies(sender, instance, created, **kwargs):
    """Run alert engine checks when a NoonReport is created."""
    if not created:
        return
    try:
        from dashboard.alert_engine import check_noon_report
        alerts = check_noon_report(instance)
        if alerts:
            logger.info(f"[Signals] {len(alerts)} alert(s) generated for NoonReport {instance.pk}")
    except Exception as e:
        logger.error(f"[Signals] Alert check failed for NoonReport: {e}")
