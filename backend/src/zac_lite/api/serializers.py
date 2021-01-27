from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField(
        label=_("detail"),
        help_text=_("Detailed information about the error."),
    )
