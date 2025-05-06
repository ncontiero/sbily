from django.urls import include
from django.urls import path

from sbily.links.views import delete_link as delete_link_view
from sbily.links.views import update_link as update_link_view

from . import views

# URLs for managing individual links
link_urlpatterns = [
    path("", views.link_statistics, name="link"),
    path("update/", update_link_view, name="update_link"),
    path("delete/", delete_link_view, name="delete_link"),
]

links_urlpatterns = [
    path("", views.links, name="links"),
    path("<str:shortened_link>/", include(link_urlpatterns)),
]

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("links/", include(links_urlpatterns)),
]
