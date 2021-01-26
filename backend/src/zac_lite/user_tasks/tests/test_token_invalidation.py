from datetime import timedelta

from django.test import SimpleTestCase, override_settings

from django_camunda.camunda_models import Task, factory
from django_camunda.utils import underscoreize
from freezegun import freeze_time

from ..tokens import token_generator

TASK_DATA = underscoreize(
    {
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
)


@override_settings(EXECUTE_TASK_TOKEN_TIMEOUT_DAYS=7)
class TokenInvalidationTests(SimpleTestCase):
    def test_valid_token(self):
        task = factory(Task, TASK_DATA)
        token = token_generator.make_token(task)

        for day in range(7):
            with self.subTest(day_offset=day):
                with freeze_time(timedelta(days=day)):
                    valid = token_generator.check_token(task, token)

                self.assertTrue(valid)

    def test_token_expired(self):
        task = factory(Task, TASK_DATA)
        token = token_generator.make_token(task)

        with freeze_time(timedelta(days=7)):
            valid = token_generator.check_token(task, token)

        self.assertFalse(valid)
