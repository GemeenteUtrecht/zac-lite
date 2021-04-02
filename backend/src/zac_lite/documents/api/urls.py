from django.urls import path

from .views import UploadDocumentView

urlpatterns = [
    path("", UploadDocumentView.as_view(), name="upload-document"),
]
