from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from zac_lite.documents.models import UploadedDocument


class UploadedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedDocument
        fields = ("uuid", "task_id", "content")

    def save(self, **kwargs):
        kwargs["file_name"] = self.validated_data["content"].name
        return super().save(**kwargs)
