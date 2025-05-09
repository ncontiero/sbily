from django.urls import include
from django.urls import path

from . import views

plan_management_urlpatterns = [
    path("upgrade/", views.upgrade_plan, name="upgrade_plan"),
    path("cancel/", views.cancel_plan, name="cancel_plan"),
    path("resume/", views.resume_plan, name="resume_plan"),
]

# Payment processing
payment_urlpatterns = [
    path("finalize_upgrade/", views.finalize_upgrade, name="finalize_upgrade"),
    path(
        "subscription_complete/",
        views.subscription_complete,
        name="subscription_complete",
    ),
    path("add_method/", views.add_payment_method, name="add_payment_method"),
    path("method_added/", views.payment_method_added, name="payment_method_added"),
]

urlpatterns = [
    path("plan/", include(plan_management_urlpatterns)),
    path("payment/", include(payment_urlpatterns)),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
