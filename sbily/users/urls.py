from django.urls import include
from django.urls import path

from . import views

account_email_urlpatterns = [
    path("", views.change_email_instructions, name="change_email_instructions"),
    path("change/<str:token>/", views.change_email, name="change_email"),
]

plan_management_urlpatterns = [
    path("upgrade/", views.upgrade_plan, name="upgrade_plan"),
    path("downgrade/", views.downgrade_plan, name="downgrade_plan"),
    path("purchase_links/", views.purchase_links, name="purchase_links"),
]

# Payment processing
payment_urlpatterns = [
    path("finalize_upgrade/", views.finalize_upgrade, name="finalize_upgrade"),
    path(
        "subscription_complete/",
        views.subscription_complete,
        name="subscription_complete",
    ),
    path("purchase_complete/", views.purchase_complete, name="purchase_complete"),
    path("add_method/", views.add_payment_method, name="add_payment_method"),
    path("method_added/", views.payment_method_added, name="payment_method_added"),
]

urlpatterns = [
    path("", views.my_account, name="my_account"),
    path("plan/", include(plan_management_urlpatterns)),
    path("payment/", include(payment_urlpatterns)),
    path("email/", include(account_email_urlpatterns)),
    path("security/", views.account_security, name="account_security"),
    path("change_password/", views.change_password, name="change_password"),
    path("resend_verify_email/", views.resend_verify_email, name="resend_verify_email"),
    path("delete_account/", views.delete_account, name="delete_account"),
    path("set_timezone/", views.set_user_timezone, name="set_user_timezone"),
    path("webhook/stripe/", views.stripe_webhook, name="stripe_webhook"),
]
