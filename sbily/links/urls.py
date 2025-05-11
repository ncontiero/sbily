from django.conf import settings
from django.urls import path

from . import views

LINK_PREFIX = getattr(settings, "LINK_PREFIX", "")


# Main URL patterns
urlpatterns = [
    # Core pages
    path("", views.home, name="home"),
    path("plans/", views.plans, name="plans"),
    path("create_link/", views.create_link, name="create_link"),
    # Link redirection
    path(
        "{prefix}<str:shortened_path>/".format(prefix=LINK_PREFIX or ""),
        views.redirect_link,
        name="redirect_link",
    ),
    path("handle_link_actions/", views.handle_link_actions, name="handle_link_actions"),
    path(
        "handle_link_activation/<str:shortened_path>/",
        views.handle_link_activation,
        name="handle_link_activation",
    ),
]
