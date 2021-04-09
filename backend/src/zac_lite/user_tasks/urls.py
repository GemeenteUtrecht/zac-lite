from django.urls import path

from .views import GetTaskConfigurationView, SubmitUserTaskView, UserLinkCreateView

urlpatterns = [
    path("user-link", UserLinkCreateView.as_view(), name="user-link-create"),
    path(
        "task-data/<str:tidb64>/<str:token>",
        GetTaskConfigurationView.as_view(),
        name="task-data-detail",
    ),
    path(
        "tasks/zac-lite:zaak-documents",
        SubmitUserTaskView.as_view(),
        name="submit-user-task",
    ),
]
