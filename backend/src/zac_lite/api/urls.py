from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularJSONAPIView,
    SpectacularRedocView,
)

urlpatterns = [
    # API schema documentation
    path("", SpectacularJSONAPIView.as_view(schema=None), name="api-schema-json"),
    path("schema", SpectacularAPIView.as_view(schema=None), name="api-schema"),
    path("docs/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-docs"),
    # actual API endpoints
    path(
        "v1/",
        include(
            [
                path("files", include("zac_lite.documents.api.urls")),
                path("", include("zac_lite.user_tasks.urls")),
            ]
        ),
    ),
]
