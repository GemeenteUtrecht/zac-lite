import base64
from datetime import date
from itertools import repeat
from typing import List

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, get_task
from django_camunda.camunda_models import Task
from django_camunda.client import get_client
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.client import ZGWClient
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac_lite.api.serializers import ErrorSerializer

from ..documents.models import DocumentServiceConfig, UploadedDocument
from .context import get_context
from .data import UserTaskData, UserTaskLink
from .parsers import NoUnderscoreBeforeNumberCamelCaseJSONParser
from .permissions import TOKEN_IN_BODY, TOKEN_IN_URL, TokenIsValid
from .serializers import (
    SubmitUserTaskSerializer,
    UserLinkSerializer,
    UserTaskConfigurationSerializer,
)
from .zaak_documents import ZaakDocumentsContext


class UserLinkCreateView(APIView):
    """
    Create a frontend URL to execute a Camunda user task.

    Given the Camunda `taskId`, an automatically-expiring signed URL is generated that
    can be shared with the intended person to execute the task. That user does not need
    to log in (using ADFS or otherwise) to be able to execute the task.
    """

    schema_summary = _("Create task user-link")
    authentication_classes = (TokenAuthentication,)
    serializer_class = UserLinkSerializer

    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(
            instance=UserTaskLink(request=request),
            data=request.data,
            context={"request": request, "view": self},
        )
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class GetTaskConfigurationView(APIView):
    """
    Retrieve the user task configuration from Camunda.

    Given the task ID and token, retrieve the task details from Camunda and enrich
    this configuration for the UI.

    The `tidb64` URL parameter is the base64 encoded task ID. The `token` URL parameter
    is used to validate access to the Camunda user task. Both parameter should be
    extracted from the frontend URL.
    """

    schema_summary = _("Retrieve user task data")
    authentication_classes = ()
    permission_classes = (TokenIsValid,)
    serializer_class = UserTaskConfigurationSerializer
    token_location = TOKEN_IN_URL

    @extend_schema(
        responses={
            200: UserTaskConfigurationSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        }
    )
    def get(self, request: Request, tidb64: str, token: str):
        task = self.get_object()
        task_data = UserTaskData(task=task, context=get_context(task))
        serializer = self.serializer_class(
            instance=task_data,
            context={"request": request, "view": self},
        )
        return Response(serializer.data)

    def get_object(self) -> Task:
        task_id = force_str(urlsafe_base64_decode(self.kwargs["tidb64"]))
        task = get_task(task_id, check_history=False)
        if task is None:
            raise exceptions.NotFound(
                _("The task with given task ID does not exist (anymore).")
            )
        # May raise a permission denied
        self.check_object_permissions(self.request, task)
        return task


class SubmitUserTaskView(APIView):
    authentication_classes = ()
    permission_classes = (TokenIsValid,)
    token_location = TOKEN_IN_BODY
    serializer_class = SubmitUserTaskSerializer
    parser_classes = (NoUnderscoreBeforeNumberCamelCaseJSONParser,)

    def post(self, request: Request) -> Response:
        task = self.get_object()
        task_context = get_context(task)

        serializer = self.serializer_class(
            data=request.data, context={"task_context": task_context}
        )
        serializer.is_valid(raise_exception=True)

        try:
            new_documents = self.create_new_documents(
                serializer.validated_data["new_documents"], task_context
            )
            updated_documents = self.update_documents(
                serializer.validated_data["replaced_documents"]
            )
        except Exception as exc:
            # Mark Camunda task as failure
            client = get_client()
            client.post(
                f"task/{task.id}/failure",
                json={"error_message": "Failed to create/update the documents"},
            )
            raise exc
        else:
            # Complete Camunda task
            complete_task(
                task_id=task.id,
                variables={
                    "updated_documents": updated_documents,
                    "new_documents": new_documents,
                },
            )

        return Response(status=status.HTTP_200_OK)

    def get_object(self) -> Task:
        task_id = force_str(urlsafe_base64_decode(self.request.data["tidb64"]))
        task = get_task(task_id, check_history=False)

        if task is None:
            raise ValidationError(
                _("The task with given task ID does not exist (anymore).")
            )

        self.check_object_permissions(self.request, task)

        return task

    def create_new_documents(
        self, documents: List, task_context: ZaakDocumentsContext
    ) -> List[str]:
        config = DocumentServiceConfig.get_solo()
        default_document_service = config.primary_drc
        if not default_document_service:
            raise RuntimeError("No default DRC service configured.")

        client = default_document_service.build_client()

        with parallel() as executor:
            new_documents_urls = executor.map(
                self._create_document, documents, repeat(task_context), repeat(client)
            )

        return list(new_documents_urls)

    def update_documents(self, documents: List) -> List[str]:
        with parallel() as executor:
            updated_documents_urls = executor.map(self._update_document, documents)

        return list(updated_documents_urls)

    def _create_document(
        self, document_data: dict, task_context: dict, client: ZGWClient
    ):
        uploaded_document = UploadedDocument.objects.get(uuid=document_data["id"])

        data = {
            "informatieobjecttype": document_data["document_type"],
            "bronorganisatie": task_context.zaak.bronorganisatie,
            "creatiedatum": date.today().isoformat(),
            "titel": uploaded_document.file_name,
            # TODO: maybe the author should be an extra field of the UploadedDocument
            "auteur": task_context.zaak.bronorganisatie,
            "taal": "nld",
            "inhoud": base64.b64encode(uploaded_document.content.read()).decode(
                "ascii"
            ),
        }

        new_document = client.create(resource="enkelvoudiginformatieobject", data=data)

        return new_document["url"]

    def _update_document(self, document_data: dict):
        client = Service.get_client(document_data["old"])

        uploaded_document = UploadedDocument.objects.get(uuid=document_data["id"])
        data = {
            "titel": uploaded_document.file_name,
            "inhoud": base64.b64encode(uploaded_document.content.read()).decode(
                "ascii"
            ),
        }

        updated_document = client.update(
            "enkelvoudiginformatieobject", url=document_data["old"], data=data
        )

        return updated_document["url"]
