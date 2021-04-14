# Generated by Django 2.2.17 on 2021-04-06 11:38

from django.db import migrations, models
import privates.fields
import privates.storages
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="UploadedDocument",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unique resource identifier (UUID4)",
                        verbose_name="UUID",
                    ),
                ),
                (
                    "file_name",
                    models.CharField(
                        help_text="Filename including extension.",
                        max_length=200,
                        verbose_name="filename",
                    ),
                ),
                (
                    "task_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="ID of the task to which the document is related",
                        verbose_name="task ID",
                    ),
                ),
                (
                    "content",
                    privates.fields.PrivateMediaFileField(
                        help_text="Content of the uploaded document",
                        storage=privates.storages.PrivateMediaFileSystemStorage(),
                        upload_to="",
                        verbose_name="content",
                    ),
                ),
            ],
            options={
                "verbose_name": "Uploaded document",
                "verbose_name_plural": "Uploaded documents",
            },
        ),
    ]
