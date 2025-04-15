# ruff: noqa: BLE001
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.http import HttpRequest
from django.shortcuts import redirect
from django.shortcuts import render

from sbily.links.models import ShortenedLink
from sbily.users.models import Token
from sbily.users.tasks import send_password_changed_email
from sbily.users.tasks import send_password_reset_email
from sbily.users.tasks import send_welcome_email
from sbily.utils.errors import BadRequestError
from sbily.utils.errors import bad_request_error
from sbily.utils.urls import reverse_with_params

from .forms import ForgotPasswordForm
from .forms import ResetPasswordForm
from .forms import SignInForm
from .forms import SignInWithEmailForm
from .forms import SignUpForm
from .tasks import send_sign_in_with_email


def get_post_auth_redirect(request, user, form):
    """
    Determine the redirect path after authentication.
    """
    if form.cleaned_data.get("plan") == "premium":
        return redirect("upgrade_plan")

    if original_link := form.cleaned_data.get("original_link"):
        link = ShortenedLink.objects.create(
            original_link=original_link,
            user=user,
        )
        messages.success(request, "Link created successfully.")
        return redirect("link", shortened_link=link.shortened_link)

    next_path = form.cleaned_data.get("next_path", "my_account")
    return redirect(next_path)


def sign_up(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                send_welcome_email.delay_on_commit(user.id)
                messages.success(
                    request,
                    "User created successfully! Please verify your email.",
                )

                return get_post_auth_redirect(request, user, form)
            except Exception as e:
                messages.error(request, f"Error signing up: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        plan = request.GET.get("plan")
        next_path = request.GET.get("next")
        original_link = request.GET.get("original_link")
        sign_in_url = reverse_with_params(
            "sign_in",
            {"next": next_path, "original_link": original_link},
        )
        form = SignUpForm(
            initial={
                "plan": plan,
                "next_path": next_path,
                "original_link": original_link,
            },
        )

    return render(request, "sign_up.html", {"form": form, "sign_in_url": sign_in_url})


def sign_in(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")

    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            try:
                user = form.cleaned_data["user"]
                login(request, user)

                return get_post_auth_redirect(request, user, form)
            except Exception as e:
                messages.error(request, f"Error signing in: {e}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        next_path = request.GET.get("next", "my_account")
        original_link = request.GET.get("original_link")
        sign_up_url = reverse_with_params(
            "sign_up",
            {"next": next_path, "original_link": original_link},
        )
        form = SignInForm(
            initial={"next_path": next_path, "original_link": original_link},
        )

    return render(request, "sign_in.html", {"form": form, "sign_up_url": sign_up_url})


def sign_in_with_email(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("my_account")
    if request.method != "POST":
        form = SignInWithEmailForm()
        return render(request, "sign_in_with_email.html", {"form": form})

    form = SignInWithEmailForm(request.POST)

    if form.is_valid():
        try:
            user = form.cleaned_data.get("user")

            send_sign_in_with_email.delay_on_commit(user.id)
            messages.success(
                request,
                "Please check your email for a sign in link.",
            )
            return redirect("sign_in")
        except Exception as e:
            messages.error(request, f"Error sending sign in link: {e!s}")
            return redirect("sign_in_with_email")

    return render(request, "sign_in_with_email.html", {"form": form})


def sign_in_with_email_verify(request: HttpRequest, token: str):
    if request.user.is_authenticated:
        return redirect("my_account")

    try:
        token = Token.objects.get(token=token, type=Token.TYPE_SIGN_IN_WITH_EMAIL)

        if token.is_expired():
            bad_request_error("Token has expired! Please request a new one")
        if not token.user.login_with_email:
            bad_request_error("Please enable login with email")

        token.delete()
        login(request, token.user)
        messages.success(request, "Signed in successfully")
        return redirect("my_account")
    except Token.DoesNotExist:
        messages.error(request, "Invalid token")
        return redirect("sign_in_with_email")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect("sign_in_with_email")
    except Exception as e:
        messages.error(request, f"An error occurred: {e}")
        return redirect("sign_in_with_email")


def sign_out(request):
    logout(request)
    return redirect("sign_in")


def verify_email(request: HttpRequest, token: str):
    user = request.user
    is_authenticated = user.is_authenticated
    redirect_url_name = (
        reverse_with_params("my_account", {"tab": "email"})
        if is_authenticated
        else "sign_in"
    )

    try:
        obj_token = Token.objects.get(token=token, type="email_verification")

        if is_authenticated and user != obj_token.user:
            bad_request_error("Invalid token")
        if obj_token.is_expired():
            bad_request_error("Token has expired! Please request a new one")
        if obj_token.user.email_verified:
            bad_request_error("Email has already been verified")

        obj_token.user.email_verified = True
        obj_token.user.save()
        obj_token.delete()
        messages.success(request, "Email verified successfully")
        return redirect(redirect_url_name)
    except Token.DoesNotExist:
        messages.error(request, "Invalid token")
        return redirect(redirect_url_name)
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect(redirect_url_name)
    except Exception as e:
        messages.error(request, f"Error verifying email: {e}")
        return redirect(redirect_url_name)


def forgot_password(request: HttpRequest):
    if request.method != "POST":
        form = ForgotPasswordForm()
        return render(request, "forgot_password.html", {"form": form})

    form = ForgotPasswordForm(request.POST)

    if form.is_valid():
        try:
            user = form.cleaned_data.get("user")
            send_password_reset_email.delay_on_commit(user.id)
            messages.success(request, "Password reset email sent successfully")
            return redirect("sign_in")
        except Exception as e:
            messages.error(request, f"Error sending password reset email: {e!s}")
            return redirect("forgot_password")

    return render(request, "forgot_password.html", {"form": form})


def reset_password(request: HttpRequest, token: str):
    try:
        obj_token = Token.objects.get(token=token, type=Token.TYPE_PASSWORD_RESET)
    except Token.DoesNotExist:
        messages.error(request, "Invalid token")
        return redirect("forgot_password")

    if obj_token.is_expired():
        messages.error(request, "Token has expired! Please request a new one")
        return redirect("forgot_password")

    if request.method != "POST":
        form = ResetPasswordForm(instance=obj_token.user)
        return render(request, "reset_password.html", {"token": token, "form": form})

    form = ResetPasswordForm(request.POST, instance=obj_token.user)

    if form.is_valid():
        try:
            user = form.save()
            obj_token.delete()
            send_password_changed_email.delay_on_commit(user.id)
            messages.success(request, "Password reset successfully")
            return redirect("sign_in")
        except Exception as e:
            messages.error(request, f"Error resetting password: {e!s}")
            return redirect("forgot_password")

    return render(request, "reset_password.html", {"token": token, "form": form})
