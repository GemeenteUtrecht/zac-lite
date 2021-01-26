from django.apps import AppConfig

from rest_framework.fields import JSONField
from zgw_consumers.drf.serializers import APIModelSerializer


class UserTasksConfig(AppConfig):
    name = "zac_lite.user_tasks"

    def ready(self):
        register_drf_types()


def register_drf_types():
    APIModelSerializer.serializer_field_mapping[dict] = JSONField
