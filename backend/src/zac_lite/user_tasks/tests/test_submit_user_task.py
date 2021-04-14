from unittest.mock import patch

from django.utils.http import urlsafe_base64_encode

import requests_mock
from django_camunda.camunda_models import Task, factory
from django_camunda.utils import serialize_variable, underscoreize
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
from ...documents.models import DocumentServiceConfig
from ...documents.tests.factories import UploadedDocumentFactory
from ..tokens import token_generator

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
    "formKey": "zac-lite:zaak-documents",
    "tenantId": "aTenantId",
}

OPENZAAK_BASE = "https://openzaak.nl"
DRC_BASE = "https://drc.nl/api/v1"
CAMUNDA_BASE = "https://camunda.example.com/engine-rest"

IOT_1 = generate_oas_component(
    "ztc",
    "schemas/InformatieObjectType",
    url=f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
    omschrijving="Plattegrond",
)

ZAAKTYPE = generate_oas_component(
    "ztc",
    "schemas/ZaakType",
    url=f"{OPENZAAK_BASE}/catalogi/api/v1/zaaktypen/ef82832d-ef1b-47d8-a830-2295ed02bdc8",
    omschrijving="Vastleggen rapportage NEN 2580",
    informatieobjecttypen=[
        f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
    ],
)

ZAAK = generate_oas_component(
    "zrc",
    "schemas/Zaak",
    url=f"{OPENZAAK_BASE}/zaken/api/v1/zaken/13c846eb-a034-4314-9035-695f030b970c",
    identificatie="ZAAK-2021-0000000001",
    zaaktype=ZAAKTYPE["url"],
)

DOCUMENT_1 = generate_oas_component(
    "drc",
    "schemas/EnkelvoudigInformatieObject",
    url=f"{DRC_BASE}/enkelvoudiginformatieobjecten/79dc383d",
    titel="Eerste verdieping",
    bestandsomvang=4096,
    informatieobjecttype=IOT_1["url"],
)
DOCUMENT_2 = generate_oas_component(
    "drc",
    "schemas/EnkelvoudigInformatieObject",
    url=f"{DRC_BASE}/enkelvoudiginformatieobjecten/079cf380",
    titel="Tweede verdieping",
    bestandsomvang=2048,
    informatieobjecttype=IOT_1["url"],
)

ZIO_1 = generate_oas_component(
    "zrc",
    "schemas/ZaakInformatieObject",
    url=f"{OPENZAAK_BASE}/zaken/api/v1/zaakinformatieobjecten/1be1e307-2d99-4502-8796-4b55df98ffde",
    uuid="1be1e307-2d99-4502-8796-4b55df98ffde",
    zaak=ZAAK,
    informatieobject=DOCUMENT_1["url"],
)
ZIO_2 = generate_oas_component(
    "zrc",
    "schemas/ZaakInformatieObject",
    url=f"{OPENZAAK_BASE}/zaken/api/v1/zaakinformatieobjecten/16feb6d7-6870-4b04-a704-79408e4dd093",
    uuid="16feb6d7-6870-4b04-a704-79408e4dd093",
    zaak=ZAAK,
    informatieobject=DOCUMENT_2["url"],
)


class SubmitUserTaskValidationTests(APITransactionTestCase):
    def _set_up_services(self):
        Service.objects.create(
            label="Zaken API",
            api_root=f"{OPENZAAK_BASE}/zaken/api/v1/",
            api_type=APITypes.zrc,
        )
        Service.objects.create(
            label="Catalogi API",
            api_root=f"{OPENZAAK_BASE}/catalogi/api/v1/",
            api_type=APITypes.ztc,
        )
        Service.objects.create(
            label="Documenten API",
            api_root=DRC_BASE,
            api_type=APITypes.drc,
        )

    def _set_up_mocks(self, m, task):
        mock_service_oas_get(m, f"{OPENZAAK_BASE}/zaken/api/v1/", "zrc")
        mock_service_oas_get(m, f"{OPENZAAK_BASE}/catalogi/api/v1/", "ztc")
        mock_service_oas_get(m, f"{DRC_BASE}/", "drc")

        m.get(
            f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
            json=TASK_DATA,
        )
        m.get(
            f"{CAMUNDA_BASE}/task/{task.id}/variables/zaakUrl?deserializeValues=false",
            json=serialize_variable(ZAAK["url"]),
        )
        m.get(
            f"{CAMUNDA_BASE}/task/{task.id}/variables/toelichtingen?deserializeValues=false",
            json=serialize_variable("Voorbeeld toelichting."),
        )
        m.get(ZAAK["url"], json=ZAAK)
        m.get(ZAAKTYPE["url"], json=ZAAKTYPE)
        m.get(
            f"{OPENZAAK_BASE}/zaken/api/v1/zaakinformatieobjecten?zaak={ZAAK['url']}",
            json=[ZIO_1, ZIO_2],
        )
        m.get(DOCUMENT_1["url"], json=DOCUMENT_1)
        m.get(DOCUMENT_2["url"], json=DOCUMENT_2)
        m.get(IOT_1["url"], json=IOT_1)

    def test_invalid_task_id_400(self):
        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        with requests_mock.Mocker() as m:
            m.get(
                f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
                status_code=404,
            )
            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [],
                    "replacedDocuments": [],
                },
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
        )

    def test_invalid_token_403(self):
        tidb64 = urlsafe_base64_encode(b"598347ee-62fc-46a2-913a-6e0788bc1b8c")

        with requests_mock.Mocker() as m:
            m.get(
                f"{CAMUNDA_BASE}/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
                json=TASK_DATA,
            )
            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": "bad-token",
                    "newDocuments": [],
                    "replacedDocuments": [],
                },
            )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_BASE}/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
        )

    def test_new_document_doesnt_exist(self):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [
                        {
                            "id": "9b9ec79d-5e04-4112-a6d1-5314cdbd172e",
                            "documentType": IOT_1["url"],
                        }
                    ],
                    "replacedDocuments": [],
                },
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response_data = response.json()

        self.assertIn("newDocuments", response_data)
        self.assertIn("id", response_data["newDocuments"][0])

    def test_replaced_document_doesnt_exist(self):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [],
                    "replacedDocuments": [
                        {
                            "id": "9b9ec79d-5e04-4112-a6d1-5314cdbd172e",
                            "old": DOCUMENT_1["url"],
                        }
                    ],
                },
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response_data = response.json()

        self.assertIn("replacedDocuments", response_data)
        self.assertIn("id", response_data["replacedDocuments"][0])

    def test_new_document_type_doesnt_exist(self):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [
                        {
                            "id": document_1.uuid,
                            "documentType": f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/123456789",
                        }
                    ],
                    "replacedDocuments": [],
                },
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response_data = response.json()

        self.assertIn("newDocuments", response_data)
        self.assertIn(
            "A document type is not part of the ZaakDocumentsContext.",
            response_data["newDocuments"],
        )

    def test_old_document_doesnt_exist(self):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [],
                    "replacedDocuments": [
                        {
                            "id": document_1.uuid,
                            "old": f"{OPENZAAK_BASE}/documenten/api/v1/enkelvoudiginformatieobjecten/123456789",
                        }
                    ],
                },
            )

        self.assertEqual(status.HTTP_400_BAD_REQUEST, response.status_code)

        response_data = response.json()

        self.assertIn("replacedDocuments", response_data)
        self.assertIn(
            "A document to be replaced is not part of the ZaakDocumentsContext.",
            response_data["replacedDocuments"],
        )

    @patch("zac_lite.user_tasks.views.SubmitUserTaskView.create_new_documents")
    @patch("zac_lite.user_tasks.views.SubmitUserTaskView.update_documents")
    @patch("zac_lite.user_tasks.views.complete_task")
    def test_valid_data(self, mock_create_new_docs, mock_update_docs, mock_camunda):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)
        document_2 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [
                        {"id": document_1.uuid, "documentType": IOT_1["url"]}
                    ],
                    "replacedDocuments": [
                        {"id": document_2.uuid, "old": DOCUMENT_1["url"]}
                    ],
                },
            )

        self.assertEqual(status.HTTP_200_OK, response.status_code)


class SubmitUserTaskTests(APITransactionTestCase):
    def _set_up_services(self):
        Service.objects.create(
            label="Zaken API",
            api_root=f"{OPENZAAK_BASE}/zaken/api/v1/",
            api_type=APITypes.zrc,
        )
        Service.objects.create(
            label="Catalogi API",
            api_root=f"{OPENZAAK_BASE}/catalogi/api/v1/",
            api_type=APITypes.ztc,
        )
        Service.objects.create(
            label="Documenten API",
            api_root=DRC_BASE,
            api_type=APITypes.drc,
        )

    def _set_up_mocks(self, m, task):
        mock_service_oas_get(m, f"{OPENZAAK_BASE}/zaken/api/v1/", "zrc")
        mock_service_oas_get(m, f"{OPENZAAK_BASE}/catalogi/api/v1/", "ztc")
        mock_service_oas_get(m, f"{DRC_BASE}/", "drc")

        m.get(
            f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
            json=TASK_DATA,
        )
        m.get(
            f"{CAMUNDA_BASE}/task/{task.id}/variables/zaakUrl?deserializeValues=false",
            json=serialize_variable(ZAAK["url"]),
        )
        m.get(
            f"{CAMUNDA_BASE}/task/{task.id}/variables/toelichtingen?deserializeValues=false",
            json=serialize_variable("Voorbeeld toelichting."),
        )
        m.get(ZAAK["url"], json=ZAAK)
        m.get(ZAAKTYPE["url"], json=ZAAKTYPE)
        m.get(
            f"{OPENZAAK_BASE}/zaken/api/v1/zaakinformatieobjecten?zaak={ZAAK['url']}",
            json=[ZIO_1, ZIO_2],
        )
        m.get(DOCUMENT_1["url"], json=DOCUMENT_1)
        m.get(DOCUMENT_2["url"], json=DOCUMENT_2)
        m.get(IOT_1["url"], json=IOT_1)

        m.post(
            f"{DRC_BASE}/enkelvoudiginformatieobjecten",
            status_code=201,
            json={
                "url": f"{OPENZAAK_BASE}/enkelvoudiginformatieobjecten/9b9ec79d-5e04-4112-a6d1-5314cdbd172e"
            },
        )
        m.put(
            DOCUMENT_1["url"],
            status_code=200,
            json={"url": DOCUMENT_1["url"]},
        )
        m.post(
            f"{CAMUNDA_BASE}/task/{task.id}/complete",
        )

    def test_valid_data(self):
        self._set_up_services()

        drc_service = Service.objects.get(
            label="Documenten API",
        )

        config = DocumentServiceConfig.get_solo()
        config.primary_drc = drc_service
        config.save()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)
        document_2 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            response = self.client.post(
                reverse("submit-user-task"),
                data={
                    "tidb64": tidb64,
                    "token": token,
                    "newDocuments": [
                        {"id": document_1.uuid, "documentType": IOT_1["url"]}
                    ],
                    "replacedDocuments": [
                        {"id": document_2.uuid, "old": DOCUMENT_1["url"]}
                    ],
                },
            )

        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_no_default_drc_configured(self):
        self._set_up_services()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)
        document_2 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            m.post(
                f"{CAMUNDA_BASE}/task/{task.id}/failure",
            )

            with self.assertRaises(
                RuntimeError, msg="No default DRC service configured."
            ):
                self.client.post(
                    reverse("submit-user-task"),
                    data={
                        "tidb64": tidb64,
                        "token": token,
                        "newDocuments": [
                            {"id": document_1.uuid, "documentType": IOT_1["url"]}
                        ],
                        "replacedDocuments": [
                            {"id": document_2.uuid, "old": DOCUMENT_1["url"]}
                        ],
                    },
                )

            self.assertEqual(
                m.request_history[-1].url, f"{CAMUNDA_BASE}/task/{task.id}/failure"
            )

    @patch("zac_lite.user_tasks.views.SubmitUserTaskView.update_documents")
    def test_error_in_document_creation_marks_task_as_failed(
        self, mock_update_documents
    ):
        mock_update_documents.raiseError.side_effect = Exception("Test exception")

        self._set_up_services()

        drc_service = Service.objects.get(
            label="Documenten API",
        )

        config = DocumentServiceConfig.get_solo()
        config.primary_drc = drc_service
        config.save()

        tidb64 = urlsafe_base64_encode(b"3764fa19-4246-4360-a311-784907f5bd11")
        task = factory(Task, underscoreize(TASK_DATA))
        token = token_generator.make_token(task)

        document_1 = UploadedDocumentFactory.create(task_id=task.id)
        document_2 = UploadedDocumentFactory.create(task_id=task.id)

        with requests_mock.Mocker() as m:
            self._set_up_mocks(m, task)

            with self.assertRaises(Exception, msg="Test exception"):
                self.client.post(
                    reverse("submit-user-task"),
                    data={
                        "tidb64": tidb64,
                        "token": token,
                        "newDocuments": [
                            {"id": document_1.uuid, "documentType": IOT_1["url"]}
                        ],
                        "replacedDocuments": [
                            {"id": document_2.uuid, "old": DOCUMENT_1["url"]}
                        ],
                    },
                )

                m.post(
                    f"{CAMUNDA_BASE}/task/{task.id}/failure",
                )

                self.assertEqual(
                    m.request_history[-1].url, f"{CAMUNDA_BASE}/task/{task.id}/failure"
                )
