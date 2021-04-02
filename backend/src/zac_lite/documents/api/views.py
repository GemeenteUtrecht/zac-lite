import uuid

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac_lite.documents.api.serializers import (
    TaskDataSerializer,
    UploadedDocumentSerializer,
)
from zac_lite.user_tasks.permissions import TOKEN_IN_BODY, TokenIsValid


class UploadDocumentView(APIView):
    """
    Uploading a temporary document.

    It expects a multipart form with:

    - `token`: token used to validate access to the Camunda user task
    - `tidb64`: the base64 encoded task ID
    - `file`: the content of the file to upload, along with the filename. If no filename is provided, the default is
    'file'
    """

    schema_summary = _("Upload a temporary document")
    serializer_class = TaskDataSerializer
    authentication_classes = ()
    permission_classes = (TokenIsValid,)
    parser_classes = (MultiPartParser,)
    token_location = TOKEN_IN_BODY

    def post(self, request: Request) -> Response:
        task_data_serializer = self.serializer_class(data=request.data)
        task_data_serializer.is_valid(raise_exception=True)

        # Check task permissions with token
        validated_task_id = self.check_task_permissions(
            request, task_data_serializer.validated_data["tidb64"]
        )

        # Store uploaded document
        document_uuid = uuid.uuid4()

        document_serializer = UploadedDocumentSerializer(
            data={
                "uuid": document_uuid,
                "file_name": task_data_serializer.validated_data["file"].name,
                "task_id": validated_task_id,
                "content": task_data_serializer.validated_data["file"],
            }
        )
        document_serializer.is_valid(raise_exception=True)
        document_serializer.save()

        return Response({"id": document_uuid}, status=status.HTTP_201_CREATED)

    def check_task_permissions(self, request: Request, tidb64: str) -> str:
        task_id = force_str(urlsafe_base64_decode(tidb64))
        task = get_task(task_id, check_history=False)

        if task is None:
            raise ValidationError(
                _("The task with given task ID does not exist (anymore).")
            )

        self.check_object_permissions(self.request, task)

        return task_id
