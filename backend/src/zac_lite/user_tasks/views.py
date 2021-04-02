from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task
from django_camunda.camunda_models import Task
from drf_spectacular.utils import extend_schema
from rest_framework import exceptions, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac_lite.api.serializers import ErrorSerializer

from .context import get_context
from .data import UserTaskData, UserTaskLink
from .permissions import TOKEN_IN_URL, TokenIsValid
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
