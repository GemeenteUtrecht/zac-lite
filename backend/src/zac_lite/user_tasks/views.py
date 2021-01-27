from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserLinkSerializer, UserTaskLink


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
