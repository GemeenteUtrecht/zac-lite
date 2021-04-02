from typing import Optional

from django_camunda.camunda_models import Task
from rest_framework import permissions, views
from rest_framework.request import Request

from .tokens import token_generator

TOKEN_IN_BODY = "TOKEN_IN_BODY"
TOKEN_IN_URL = "TOKEN_IN_URL"


class TokenIsValid(permissions.BasePermission):
    token_kwarg = "token"

    def has_permission(self, request: Request, view: views.APIView) -> bool:
        if not self.get_token(request, view):
            return False
        return True

    def has_object_permission(self, request: Request, view: views.APIView, obj: Task):
        token = self.get_token(request, view)
        return token_generator.check_token(obj, token)

    def get_token(self, request: Request, view: views.APIView) -> Optional[str]:
        if view.token_location == TOKEN_IN_BODY:
            data = request.data
        else:
            data = request.resolver_match.kwargs

        if self.token_kwarg in data:
            return data[self.token_kwarg]

        return None
