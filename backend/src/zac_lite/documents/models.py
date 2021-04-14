import uuid as _uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from privates.fields import PrivateMediaFileField


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
