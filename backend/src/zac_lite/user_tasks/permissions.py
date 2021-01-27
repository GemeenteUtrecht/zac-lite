from django_camunda.camunda_models import Task
from rest_framework import permissions, views
from rest_framework.request import Request

from .tokens import token_generator


class TokenIsValid(permissions.BasePermission):
    token_kwarg = "token"

    def has_permission(self, request: Request, view: views.APIView) -> bool:
        resolver_kwargs = request.resolver_match.kwargs
        if self.token_kwarg not in resolver_kwargs:
            return False
        return True

    def has_object_permission(self, request: Request, view: views.APIView, obj: Task):
        token = request.resolver_match.kwargs[self.token_kwarg]
        return token_generator.check_token(obj, token)
