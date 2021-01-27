from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from django_camunda.camunda_models import Task
from rest_framework import serializers
from rest_framework.request import Request

from .tokens import token_generator

FRONTEND_URL = "/ui/perform-task/{tidb64}/{token}"


@dataclass
class UserTaskLink:
    request: Request
    task: Optional[Task] = None

    @property
    def task_id(self):
        return self.task.id

    @property
    def url(self):
        assert self.task is not None, "Expected task to be validated and resolved"
        tidb64 = urlsafe_base64_encode(force_bytes(self.task.id))
        token = token_generator.make_token(self.task)
        ui_path = FRONTEND_URL.format(tidb64=tidb64, token=token)
        return self.request.build_absolute_uri(ui_path)


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
