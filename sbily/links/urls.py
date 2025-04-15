from django.conf import settings
from django.urls import include
from django.urls import path

from . import views

LINK_PREFIX = getattr(settings, "LINK_PREFIX", "")

# URLs for managing individual links
link_urlpatterns = [
    path("", views.link, name="link"),
    path("update/", views.update_link, name="update_link"),
    path("delete/", views.delete_link, name="delete_link"),
]


# Main URL patterns
urlpatterns = [
    # Core pages
    path("", views.home, name="home"),
    path("plans/", views.plans, name="plans"),
    path("create_link/", views.create_link, name="create_link"),
    # Link redirection
    path(
        "{prefix}<str:shortened_link>/".format(prefix=LINK_PREFIX or ""),
        views.redirect_link,
        name="redirect_link",
    ),
    # Include sub-patterns
    path("links/", views.links, name="links"),
    path("link/<str:shortened_link>/", include(link_urlpatterns)),
    path("handle_link_actions/", views.handle_link_actions, name="handle_link_actions"),
]
