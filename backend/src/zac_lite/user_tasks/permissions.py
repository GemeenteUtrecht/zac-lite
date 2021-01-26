from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from django_camunda.api import get_task
from rest_framework import permissions, views
from rest_framework.request import Request

from .tokens import token_generator


class TokenIsValid(permissions.BasePermission):
    task_id_kwarg = "tidb64"
    token_kwarg = "token"

    def has_permission(self, request: Request, view: views.APIView) -> bool:
        resolver_kwargs = request.resolver_match.kwargs
        if (
            self.task_id_kwarg not in resolver_kwargs
            or self.token_kwarg not in resolver_kwargs
        ):
            return False

        task_id = force_str(urlsafe_base64_decode(resolver_kwargs[self.task_id_kwarg]))
        token = resolver_kwargs[self.token_kwarg]

        # fetch the task to validate the token
        task = get_task(task_id, check_history=False)
        if task is None:
            return False

        valid_token = token_generator.check_token(task, token)
        if valid_token:
            view.task = task
        return valid_token
