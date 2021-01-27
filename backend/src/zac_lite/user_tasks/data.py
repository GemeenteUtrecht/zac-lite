from dataclasses import dataclass
from typing import Optional

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from django_camunda.camunda_models import Task
from rest_framework.request import Request

from .tokens import token_generator
from .zaak_documents import ZaakDocumentsContext

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


@dataclass
class UserTaskData:
    task: Task
    context: ZaakDocumentsContext
