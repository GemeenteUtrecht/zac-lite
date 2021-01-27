from django.utils.http import urlsafe_base64_decode

import requests_mock
from rest_framework import status
from rest_framework.reverse import reverse_lazy
from rest_framework.test import APITestCase

from zac_lite.accounts.tests.factories import UserFactory

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


class LinkGenerationTests(APITestCase):

    endpoint = reverse_lazy("user-link-create")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory.create(with_token=True)

    def test_generate_link_auth_required(self):
        response = self.client.post(
            self.endpoint, {"taskId": "598347ee-62fc-46a2-913a-6e0788bc1b8c"}
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @requests_mock.Mocker()
    def test_generate_link_authenticated(self, m):
        m.get(
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
            json=TASK_DATA,
        )

        response = self.client.post(
            self.endpoint,
            {"taskId": "598347ee-62fc-46a2-913a-6e0788bc1b8c"},
            HTTP_AUTHORIZATION=f"Token {self.user.auth_token.key}",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response_data = response.json()
        self.assertIn("url", response_data)

        url = response_data["url"]
        self.assertTrue(url.startswith("http://testserver"))

        (*rest, tidb64, token) = url.split("/")
        task_id = urlsafe_base64_decode(tidb64)
        self.assertEqual(task_id, b"598347ee-62fc-46a2-913a-6e0788bc1b8c")
