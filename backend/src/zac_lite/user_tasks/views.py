from django.utils.translation import gettext_lazy as _

from django_camunda.camunda_models import Task
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .data import UserTaskData, UserTaskLink
from .permissions import TokenIsValid
from .serializers import UserLinkSerializer, UserTaskConfigurationSerializer


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

    task: Task = None  # set by the :class:`TokenIsValid` permission class

    def get(self, request: Request, tidb64: str, token: str):
        task_data = UserTaskData(task=self.task, context={"foo": "bar"})
        serializer = self.serializer_class(
            instance=task_data,
            context={"request": request, "view": self},
        )
        return Response(serializer.data)
