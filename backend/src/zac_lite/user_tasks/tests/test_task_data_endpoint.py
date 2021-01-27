from django.utils.http import urlsafe_base64_encode

import requests_mock
from django_camunda.camunda_models import Task, factory
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.reverse import reverse, reverse_lazy
from rest_framework.test import APITestCase

from ..tokens import token_generator

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": "anAssignee",
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "aProcDefId",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "aFormKey",
    "tenantId": "aTenantId",
}


class GetTaskDataTests(APITestCase):
    def test_invalid_task_id_404(self):
        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)
        endpoint = reverse(
            "task-data-detail",
            kwargs={
                "tidb64": tidb64,
                "token": token,
            },
        )

        with requests_mock.Mocker() as m:
            m.get(
                "https://camunda.example.com/engine-rest/task/3764fa19-4246-4360-a311-784907f5bd11",
                status_code=404,
            )
            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            m.last_request.url,
            "https://camunda.example.com/engine-rest/task/3764fa19-4246-4360-a311-784907f5bd11",
        )

    def test_invalid_token_403(self):
        tidb64 = urlsafe_base64_encode(b"598347ee-62fc-46a2-913a-6e0788bc1b8c")
        endpoint = reverse(
            "task-data-detail",
            kwargs={
                "tidb64": tidb64,
                "token": "bad-token",
            },
        )

        with requests_mock.Mocker() as m:
            m.get(
                "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
                json=TASK_DATA,
            )
            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            m.last_request.url,
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
        )
