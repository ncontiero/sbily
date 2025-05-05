from django.conf import settings

LINK_BASE_URL = getattr(settings, "LINK_BASE_URL", None)


def link_base_url(request):
    return {"LINK_BASE_URL": LINK_BASE_URL}
