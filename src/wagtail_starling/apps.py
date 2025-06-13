# wagtail_custom_tabs/apps.py
from django.apps import AppConfig

class WagtailStarlingConfig(AppConfig):
    name = 'wagtail_starling'
    verbose_name = "Wagtail Starling"

    def ready(self):
        pass
