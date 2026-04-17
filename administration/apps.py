import os
import threading

from django.apps import AppConfig


class AdministrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administration'
    verbose_name = '⚓ MarineMind Operations'

    def ready(self):
        import administration.signals  # noqa: F401

        # Customise the default admin site branding
        from django.contrib import admin
        admin.site.site_header = 'MarineMind'
        admin.site.site_title = 'MarineMind Admin'
        admin.site.index_title = 'Control Center'
        admin.site.site_url = '/'

        # Auto-seed noon reports once (only in the main runserver process)
        if os.environ.get('RUN_MAIN') == 'true':
            threading.Thread(target=self._auto_seed_noon_reports, daemon=True).start()

    @staticmethod
    def _auto_seed_noon_reports():
        """Seed noon reports if none exist — runs once on startup."""
        try:
            from administration.models import NoonReport
            if not NoonReport.objects.exists():
                from django.core.management import call_command
                call_command('seed_noon_reports')
        except Exception:
            pass  # silently skip if DB isn't ready (e.g. migrations pending)
