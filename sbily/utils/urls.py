from urllib.parse import urlencode

from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from sbily.utils.data import is_none


def reverse_with_params(
    url_name: str,
    params: dict | None = None,
) -> str:
    """Reverses a URL pattern with optional query parameters.

    Args:
        url_name: The name of the URL pattern
        params: Optional dictionary of query parameters

    Returns:
        URL string with query parameters if provided
    """
    url_path = reverse(url_name)

    if not params:
        return url_path

    filtered_params = {k: v for k, v in params.items() if not is_none(v)}
    if not filtered_params:
        return url_path

    query_string = urlencode(filtered_params)
    if url_path.endswith("/"):
        url_path = url_path[:-1]

    return f"{url_path}?{query_string}"


def redirect_with_params(
    url_name: str,
    params: dict | None = None,
) -> HttpResponseRedirect:
    """Redirects to a URL with optional query parameters.

    Args:
        url_name: The name of the URL pattern.
        params: A dictionary of query parameters.

    Returns:
        An HTTP redirect response.

    Example:
        >>> redirect_with_params("sign_in", {"next": "/account/me/"})
        HttpResponseRedirect("/auth/sign_in/?next=/account/me/")
    """
    url = reverse_with_params(url_name, params)
    return redirect(url)


def redirect_with_tab(tab: str, **kwargs):
    """Redirects to the 'my_account' URL with a specified tab.

    Args:
        tab: The name of the tab to redirect to.
        **kwargs: Additional query parameters.

    Returns:
        An HTTP redirect response.
    """
    params = {"tab": tab, **kwargs}
    return redirect_with_params("my_account", params)
