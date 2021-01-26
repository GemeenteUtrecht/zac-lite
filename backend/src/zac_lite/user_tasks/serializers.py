from typing import Optional
from uuid import UUID

from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from django_camunda.camunda_models import Task
from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from .data import UserTaskData


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


class UserTaskConfigurationSerializer(APIModelSerializer):
    form = serializers.CharField(
        label=_("Form to render"),
        source="task.form_key",
        help_text=_("The form key of the form to render."),
    )
    task = TaskSerializer()

    class Meta:
        model = UserTaskData
        fields = (
            "form",
            "task",
            "context",
        )
