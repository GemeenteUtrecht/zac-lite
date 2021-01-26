from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserLinkSerializer, UserTaskLink


class UserLinkCreateView(APIView):
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
