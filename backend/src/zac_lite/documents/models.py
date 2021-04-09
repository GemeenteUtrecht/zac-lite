import uuid as _uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from privates.fields import PrivateMediaFileField
from solo.models import SingletonModel
from zgw_consumers.constants import APITypes


class UploadedDocument(models.Model):
    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        default=_uuid.uuid4,
        help_text=_("Unique resource identifier (UUID4)"),
    )
    file_name = models.CharField(
        verbose_name=_("filename"),
        max_length=200,
        help_text=_("Filename including extension."),
    )
    task_id = models.UUIDField(
        verbose_name=_("task ID"),
        default=_uuid.uuid4,
        help_text=_("ID of the task to which the document is related"),
    )
    content = PrivateMediaFileField(
        verbose_name=_("content"),
        upload_to="",
        help_text=_("Content of the uploaded document"),
    )

    class Meta:
        verbose_name = _("Uploaded document")
        verbose_name_plural = _("Uploaded documents")

    def __str__(self):
        return self.file_name


class DocumentServiceConfig(SingletonModel):
    primary_drc = models.ForeignKey(
        "zgw_consumers.Service",
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"api_type": APITypes.drc},
        verbose_name=_("primary DRC"),
        help_text=_("Document API where new documents will be created."),
    )

    class Meta:
        verbose_name = _("document serivce configuration")
        verbose_name_plural = _("document serivce configurations")

    def __str__(self):
        return "Default document service configuration"
