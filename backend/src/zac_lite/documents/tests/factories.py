import uuid

import factory


class UploadedDocumentFactory(factory.django.DjangoModelFactory):
    # uuid = factory.fuzzy.FuzzyAttribute(uuid.uuid4)
    content = factory.django.FileField(data=b"Some test data")

    class Meta:
        model = "documents.UploadedDocument"
