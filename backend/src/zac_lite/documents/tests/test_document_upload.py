import io

from django.utils.http import urlsafe_base64_encode

import requests_mock
from django_camunda.camunda_models import Task, factory
from django_camunda.utils import underscoreize
from privates.test import temp_private_root
from rest_framework import status
from rest_framework.test import APITestCase

from ...user_tasks.tokens import token_generator
from ..models import UploadedDocument

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "3764fa19-4246-4360-a311-784907f5bd11",
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

CAMUNDA_BASE = "https://camunda.example.com/engine-rest"


@temp_private_root()
class DocumentUploadTests(APITestCase):
    def test_can_upload_document(self):
        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        file = io.StringIO("Some content data")
        file.name = "test.txt"

        with requests_mock.Mocker() as m:
            m.get(
                f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
                json=TASK_DATA,
            )
            response = self.client.post(
                "/api/v1/files",
                {
                    "file": file,
                    "token": token,
                    "tidb64": tidb64,
                },
                format="multipart",
            )

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        data = response.json()

        self.assertIn("id", data)

        uploaded_documents = UploadedDocument.objects.filter(uuid=data["id"])

        self.assertEqual(1, uploaded_documents.count())

        document = uploaded_documents.first()
        document.content.seek(0)

        self.assertEqual("test.txt", document.file_name)
        self.assertEqual(task.id, document.task_id)
        self.assertEqual(b"Some content data", document.content.read())

        # Check that the url of the document is not accessible
        response = self.client.get(document.content.url)

        self.assertEqual(status.HTTP_404_NOT_FOUND, response.status_code)

    def test_invalid_token(self):
        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        token = "bad-token"

        file = io.StringIO("Some content data")
        file.name = "test.txt"

        with requests_mock.Mocker() as m:
            m.get(
                f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
                json=TASK_DATA,
            )
            response = self.client.post(
                "/api/v1/files",
                {
                    "file": file,
                    "token": token,
                    "tidb64": tidb64,
                },
                format="multipart",
            )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_non_existent_task(self):
        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        file = io.StringIO("Some content data")
        file.name = "test.txt"

        with requests_mock.Mocker() as m:
            m.get(
                f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
                status_code=404,
            )
            response = self.client.post(
                "/api/v1/files",
                {
                    "file": file,
                    "token": token,
                    "tidb64": tidb64,
                },
                format="multipart",
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)
