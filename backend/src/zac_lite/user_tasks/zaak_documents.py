from dataclasses import dataclass
from typing import Any, Dict, Iterator, List

from django_camunda.api import get_task_variable
from django_camunda.camunda_models import Task
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service


@dataclass
class ZaakDocumentsContext:
    zaak: Zaak
    documents: List[Document]
    document_types: List[InformatieObjectType]
    toelichtingen: str


def get_zaak_documents_context(task: Task) -> ZaakDocumentsContext:
    """
    Fetch the required information from the upstream API's to build the context.
    """

    # get the task/process variables
    with parallel() as executor:
        zaak_url_future = executor.submit(get_task_variable, task.id, "zaakUrl")
        toelichtingen_future = executor.submit(
            get_task_variable, task.id, "toelichtingen"
        )

        zaak_url = zaak_url_future.result()
        toelichtingen = toelichtingen_future.result()

    # next - retrieve the Zaak & related objects
    zaken_client = Service.get_client(zaak_url)
    assert zaken_client is not None, f"Could not determine client for URL {zaak_url}"
    # ensure the schema is cached on the client before entering threads
    zaken_client.schema
    with parallel() as executor:
        zaak_future = executor.submit(zaken_client.retrieve, "zaak", url=zaak_url)
        zios_future = executor.submit(
            zaken_client.list, "zaakinformatieobject", query_params={"zaak": zaak_url}
        )

        zaak = factory(Zaak, zaak_future.result())
        zios = zios_future.result()

    # and extract the relations from the zaak/zio responses:
    # * get the zaaktype
    # * get the documents
    catalogi_client = Service.get_client(zaak.zaaktype)
    # ensure that the schema is cached on the instance
    catalogi_client.schema
    with parallel() as executor:
        zaaktype_future = executor.submit(
            catalogi_client.retrieve, "zaaktype", url=zaak.zaaktype
        )
        documents = get_zaak_documents(executor, zios)

        zaak.zaaktype = factory(ZaakType, zaaktype_future.result())

    # finally, fetch the informatieobjecttypen
    iot_urls = zaak.zaaktype.informatieobjecttypen
    with parallel() as executor:
        iots: Iterator[dict] = executor.map(
            lambda url: catalogi_client.retrieve("informatieobjecttype", url=url),
            iot_urls,
        )
    document_types = factory(InformatieObjectType, list(iots))

    return ZaakDocumentsContext(
        zaak=zaak,
        documents=list(documents),
        document_types=document_types,
        toelichtingen=toelichtingen,
    )


def get_zaak_documents(executor, zios: List[Dict[str, Any]]) -> Iterator[Document]:
    document_clients = []
    io_and_clients = []
    for zio in zios:
        io = zio["informatieobject"]
        for client in document_clients:
            if io.startswith(client.base_url):
                io_and_clients.append((io, client))
                break
        else:
            client = Service.get_client(io)
            io_and_clients.append((io, client))
            document_clients.append(client)

    def _retrieve_document(io_and_client: tuple) -> Document:
        url, client = io_and_client
        doc_data = client.retrieve("enkelvoudiginformatieobject", url=url)
        return factory(Document, doc_data)

    # make sure that all the API specs are fetched _before_ entering threads
    # (that invalidate caches)
    with parallel() as _nested_executor:
        _nested_executor.map(lambda client: client.schema, document_clients)

    return executor.map(_retrieve_document, io_and_clients)
