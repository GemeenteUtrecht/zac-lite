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
        fields = ("uuid", "file_name", "task_id", "content")


class TaskDataSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1000)
    tidb64 = serializers.CharField(max_length=1000)
    file = serializers.FileField(max_length=100, use_url=False)
