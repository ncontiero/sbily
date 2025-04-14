from django.urls import include
from django.urls import path

from . import views

auth_sign_in_urlpatterns = [
    path("", views.sign_in, name="sign_in"),
    path("with_email/", views.sign_in_with_email, name="sign_in_with_email"),
    path(
        "with_email/<str:token>/",
        views.sign_in_with_email_verify,
        name="sign_in_with_email_verify",
    ),
]

urlpatterns = [
    path("sign_up/", views.sign_up, name="sign_up"),
    path("sign_in/", include(auth_sign_in_urlpatterns)),
    path("sign_out/", views.sign_out, name="sign_out"),
    path("verify_email/<str:token>/", views.verify_email, name="verify_email"),
    path("forgot_password/", views.forgot_password, name="forgot_password"),
    path("reset_password/<str:token>/", views.reset_password, name="reset_password"),
]
