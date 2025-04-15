from django.urls import include
from django.urls import path

from . import views

account_email_urlpatterns = [
    path("", views.change_email_instructions, name="change_email_instructions"),
    path("change/<str:token>/", views.change_email, name="change_email"),
]

urlpatterns = [
    path("", views.my_account, name="my_account"),
    path("email/", include(account_email_urlpatterns)),
    path("security/", views.account_security, name="account_security"),
    path("change_password/", views.change_password, name="change_password"),
    path("resend_verify_email/", views.resend_verify_email, name="resend_verify_email"),
    path("delete_account/", views.delete_account, name="delete_account"),
    path("set_timezone/", views.set_user_timezone, name="set_user_timezone"),
]
