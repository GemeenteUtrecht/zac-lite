import logging
from typing import Optional

from django_camunda.camunda_models import Task

from .zaak_documents import ZaakDocumentsContext, get_zaak_documents_context

logger = logging.getLogger(__name__)

FORM_KEY_MAP = {
    "zac-lite:zaak-documents": get_zaak_documents_context,
}


class EmptyContext:
    def __getattr__(self, key):
        return None


def get_context(task: Task) -> Optional[ZaakDocumentsContext]:
    getter = FORM_KEY_MAP.get(task.form_key)
    if getter is None:
        logger.warning("No context handler for form key %s", task.form_key)
        return None

    return getter(task)
