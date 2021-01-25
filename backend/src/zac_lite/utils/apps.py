from django.apps import AppConfig


class UtilsConfig(AppConfig):
    name = "zac_lite.utils"

    def ready(self):
        from . import checks  # noqa
