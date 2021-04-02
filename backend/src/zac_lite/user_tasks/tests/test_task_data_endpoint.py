import uuid

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import requests_mock
from django_camunda.camunda_models import Task, factory
from django_camunda.utils import serialize_variable, underscoreize
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

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

OPENZAAK_BASE = "https://openzaak.utrechtproeftuin.nl"
DRC_BASE = "https://drc.utrechtproeftuin.nl/api/v1"
CAMUNDA_BASE = "https://camunda.example.com/engine-rest"


def get_endpoint(task: Task):
    tidb64 = urlsafe_base64_encode(force_bytes(task.id))
    token = token_generator.make_token(task)
    return reverse("task-data-detail", kwargs={"tidb64": tidb64, "token": token})


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
                f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
                status_code=404,
            )
            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_BASE}/task/3764fa19-4246-4360-a311-784907f5bd11",
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
                f"{CAMUNDA_BASE}/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
                json=TASK_DATA,
            )
            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_BASE}/task/598347ee-62fc-46a2-913a-6e0788bc1b8c",
        )


ZAAKTYPE = generate_oas_component(
    "ztc",
    "schemas/ZaakType",
    url=f"{OPENZAAK_BASE}/catalogi/api/v1/zaaktypen/ef82832d-ef1b-47d8-a830-2295ed02bdc8",
    omschrijving="Vastleggen rapportage NEN 2580",
    informatieobjecttypen=[
        f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
        f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
    ],
)

IOT_1 = generate_oas_component(
    "ztc",
    "schemas/InformatieObjectType",
    url=f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
    omschrijving="Plattegrond",
)

IOT_2 = generate_oas_component(
    "ztc",
    "schemas/InformatieObjectType",
    url=f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
    omschrijving="bijlage",
)

ZAAK = generate_oas_component(
    "zrc",
    "schemas/Zaak",
    url=f"{OPENZAAK_BASE}/zaken/api/v1/zaken/13c846eb-a034-4314-9035-695f030b970c",
    identificatie="ZAAK-2021-0000000001",
    zaaktype=ZAAKTYPE["url"],
)


def get_zio(zaak: str, io: str):
    _uuid = uuid.uuid4()
    return generate_oas_component(
        "zrc",
        "schemas/ZaakInformatieObject",
        url=f"{OPENZAAK_BASE}/zaken/api/v1/zaakinformatieobjecten/{_uuid}",
        uuid=str(_uuid),
        zaak=zaak,
        informatieobject=io,
    )


class ZaakDocumentsFormKeyTests(APITransactionTestCase):
    """
    Test the endpoint behaviour specifically for the zac-lite:zaak-documents form key.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

    def test_valid_response(self):
        task_data = {**TASK_DATA, "formKey": "zac-lite:zaak-documents"}
        task = factory(Task, underscoreize(task_data))
        doc_1 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DRC_BASE}/enkelvoudiginformatieobjecten/79dc383d",
            titel="Eerste verdieping",
            bestandsomvang=4096,
            informatieobjecttype=IOT_1["url"],
        )
        doc_2 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DRC_BASE}/enkelvoudiginformatieobjecten/079cf380",
            titel="Tweede verdieping",
            bestandsomvang=2048,
            informatieobjecttype=IOT_1["url"],
        )
        zios = [
            get_zio(ZAAK["url"], doc_1["url"]),
            get_zio(ZAAK["url"], doc_2["url"]),
        ]
        endpoint = get_endpoint(task)

        with requests_mock.Mocker() as m:
            mock_service_oas_get(m, f"{OPENZAAK_BASE}/zaken/api/v1/", "zrc")
            mock_service_oas_get(m, f"{OPENZAAK_BASE}/catalogi/api/v1/", "ztc")
            mock_service_oas_get(m, f"{DRC_BASE}/", "drc")
            m.get(f"{CAMUNDA_BASE}/task/{task.id}", json=task_data)
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
                json=zios,
            )
            m.get(doc_1["url"], json=doc_1)
            m.get(doc_2["url"], json=doc_2)
            m.get(IOT_1["url"], json=IOT_1)
            m.get(IOT_2["url"], json=IOT_2)

            response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = {
            "form": "zac-lite:zaak-documents",
            "task": {
                "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
                "name": "aName",
                "assignee": "anAssignee",
                "created": "2013-01-23T11:42:42Z",
            },
            "context": {
                "zaak": {
                    "identificatie": "ZAAK-2021-0000000001",
                    "zaaktype": {"omschrijving": "Vastleggen rapportage NEN 2580"},
                },
                "documents": [
                    {
                        "url": f"{DRC_BASE}/enkelvoudiginformatieobjecten/79dc383d",
                        "title": "Eerste verdieping",
                        "size": 4096,
                        "documentType": f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
                    },
                    {
                        "url": f"{DRC_BASE}/enkelvoudiginformatieobjecten/079cf380",
                        "title": "Tweede verdieping",
                        "size": 2048,
                        "documentType": f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
                    },
                ],
                "documentTypes": [
                    {
                        "url": f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/1a1d4fb2",
                        "omschrijving": "Plattegrond",
                    },
                    {
                        "url": f"{OPENZAAK_BASE}/catalogi/api/v1/informatieobjecttypen/63eb5ef4",
                        "omschrijving": "bijlage",
                    },
                ],
                "toelichtingen": "Voorbeeld toelichting.",
            },
        }
        self.maxDiff = None
        self.assertEqual(response_data, expected)
        # expected network calls:
        # * fetch task from Camunda API (+1)
        # * fetch zaakUrl & toelichtingen variables from Camunda API (+2)
        # * 3 x OAS get (zrc, drc, ztc)
        # * fetch zaak from Open Zaak (+1)
        # * fetch zaaktype from Open Zaak (+1)
        # * fetch zaak-documents from Open Zaak (+1)
        # * fetch 2 documents from Documenten API (+2)
        # * fetch zaaktype-informatieobjecttypen from Open Zaak (+2)
        self.assertEqual(
            len(m.request_history),
            3 + 10,
        )
