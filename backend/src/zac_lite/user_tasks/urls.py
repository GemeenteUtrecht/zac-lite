from django.urls import path

from .views import UserLinkCreateView

urlpatterns = [
    path("user-link", UserLinkCreateView.as_view(), name="user-link-create"),
]
