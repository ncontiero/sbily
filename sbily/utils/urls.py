from django.shortcuts import redirect
from django.urls import reverse


def redirect_with_tab(tab: str, **kwargs):
    """Redirects to the 'my_account' URL with a specified tab.

    Args:
        tab: The name of the tab to redirect to.
        **kwargs: Additional query parameters.

    Returns:
        An HTTP redirect response.
    """
    params = {"tab": tab, **kwargs}
    return redirect(reverse("my_account", query=params))
