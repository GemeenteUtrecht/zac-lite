from typing import Optional
from uuid import UUID

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from django_camunda.camunda_models import Task
from rest_framework import serializers
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.drf.serializers import APIModelSerializer

from .data import UserTaskData
from .zaak_documents import ZaakDocumentsContext


class UserLinkSerializer(serializers.Serializer):
    task_id = serializers.UUIDField(
        required=True,
        label=_("Camunda Task ID"),
        help_text=_(
            "The ID of the user task in Camunda, which is normally in the UUID 4 format."
        ),
    )
    url = serializers.URLField(
        read_only=True,
        label=_("End-user URL"),
        help_text=_(
            "Fully qualified URL to the UI, intended to be opened by end-user "
            "completing the task. The URL contains a signed token, ensuring the task "
            "can only be executed once. Anyone with this URL can execute the task, so "
            "keep it secret."
        ),
    )

    def validate_task_id(self, value: UUID):
        task: Optional[Task] = get_task(value, check_history=False)
        if task is None:
            raise serializers.ValidationError(
                _(
                    "The task with task ID {task_id} could not be found in the Camunda API"
                ).format(task_id=value),
                code="not-found",
            )
        self.instance.task = task
        return value


class TaskSerializer(APIModelSerializer):
    class Meta:
        model = Task
        fields = ("id", "name", "assignee", "created")
        extra_kwargs = {
            "created": {
                "default_timezone": timezone.utc,
            },
            "assignee": {
                "allow_null": True,
            },
        }


class ZaaktypeSerializer(APIModelSerializer):
    class Meta:
        model = ZaakType
        fields = ("omschrijving",)


class ZaakSerializer(APIModelSerializer):
    zaaktype = ZaaktypeSerializer()

    class Meta:
        model = Zaak
        fields = ("identificatie", "zaaktype")


class DocumentSerializer(APIModelSerializer):
    class Meta:
        model = Document
        fields = (
            "url",
            "title",
            "size",
            "document_type",
        )
        extra_kwargs = {
            "title": {"source": "titel"},
            "size": {
                "source": "bestandsomvang",
                "help_text": _("File size in bytes"),
            },
            "document_type": {
                "source": "informatieobjecttype",
                "help_text": _("URL to the informatieobjecttype API resource"),
            },
        }


class DocumentTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class ZaakDocumentsContextSerializer(APIModelSerializer):
    zaak = ZaakSerializer()
    documents = DocumentSerializer(many=True)
    document_types = DocumentTypeSerializer(many=True)

    class Meta:
        model = ZaakDocumentsContext
        fields = ("zaak", "documents", "document_types", "toelichtingen")


class UserTaskConfigurationSerializer(APIModelSerializer):
    form = serializers.CharField(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_("The form key of the form to render."),
    )
    task = TaskSerializer(label=_("User task summary"))
    context = ZaakDocumentsContextSerializer(
        label=_("User task context"),
        help_text=_(
            "The task context shape depends on the `form` property. The value will be "
            "`null` if the backend does not 'know' the user task `formKey`."
        ),
        allow_null=True,
    )

    class Meta:
        model = UserTaskData
        fields = (
            "form",
            "task",
            "context",
        )
