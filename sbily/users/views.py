# ruff: noqa: BLE001
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render

from sbily.users.models import Token
from sbily.users.models import User
from sbily.users.tasks import send_deleted_account_email
from sbily.users.tasks import send_email_change_instructions
from sbily.users.tasks import send_email_changed_email
from sbily.users.tasks import send_email_verification
from sbily.users.tasks import send_password_changed_email
from sbily.utils.data import validate
from sbily.utils.data import validate_password
from sbily.utils.errors import BadRequestError
from sbily.utils.errors import bad_request_error
from sbily.utils.urls import redirect_with_params

from .forms import ProfileForm


def redirect_with_tab(tab: str, **kwargs):
    params = {"tab": tab, **kwargs}
    return redirect_with_params("my_account", params)


@login_required
def my_account(request: HttpRequest):
    user = request.user

    if request.method != "POST":
        token = request.GET.get("token", None)
        form = ProfileForm(instance=user)
        return render(request, "account.html", {"token": token, "form": form})

    form = ProfileForm(request.POST, instance=user)
    if form.is_valid():
        if form.has_changed():
            form.save()
            messages.success(request, "Successfully updated profile!")
        else:
            messages.warning(request, "There were no changes!")
        return redirect("my_account")

    return render(request, "account.html", {"form": form})


@login_required
def upgrade_plan(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user = request.user
        if user.is_premium:
            bad_request_error("You are already a premium user")

        user.upgrade_to_premium()
        messages.success(request, "Successfully upgraded to premium!")
        return redirect_with_tab("plan")
    except BadRequestError as e:
        messages.error(request, e.message)


@login_required
def downgrade_plan(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user = request.user
        if not user.is_premium:
            bad_request_error("You are not a premium user")

        message = user.downgrade_to_free()
        if message:
            messages.warning(request, message)

        messages.success(request, "Successfully downgraded to free!")
        return redirect_with_tab("plan")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("plan")
    except Exception as e:
        messages.error(request, f"Error downgrading to free: {e}")
        return redirect_with_tab("plan")


@login_required
def change_email_instructions(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("email")

    try:
        user = request.user
        if not user.email_verified:
            bad_request_error("Please verify your email first")
        send_email_change_instructions.delay_on_commit(user.id)
        messages.success(request, "Please check your email for instructions")
        return redirect_with_tab("email")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("email")
    except Exception as e:
        messages.error(request, f"Error sending instructions email: {e}")
        return redirect_with_tab("email")


@login_required
def change_email(request: HttpRequest, token: str):
    try:
        token_obj = Token.objects.get(
            token=token,
            type=Token.TYPE_CHANGE_EMAIL,
            user=request.user,
        )

        if request.method != "POST":
            return redirect_with_tab("email", token=token)

        user = request.user
        if not user.email_verified:
            bad_request_error("Please verify your email first")

        new_email = request.POST.get("new_email") or ""

        if not validate([new_email]):
            bad_request_error("Please fill in all fields")
        if user.email == new_email:
            bad_request_error("The new email cannot be the same as the old email")
        if User.objects.filter(email=new_email).exists():
            bad_request_error("The new email is already in use")

        old_email = user.email
        user.email = new_email
        user.email_verified = False
        user.save()
        token_obj.delete()

        send_email_changed_email.delay_on_commit(user.id, old_email)

        messages.success(
            request,
            "Email changed successfully! Please check your email for the verification link.",  # noqa: E501
        )
        return redirect_with_tab("email")
    except Token.DoesNotExist:
        messages.error(request, "Invalid token")
        return redirect_with_tab("email")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect("change_email", token=token)
    except Exception as e:
        messages.error(request, f"Error changing email: {e}")
        return redirect("change_email", token=token)


@login_required
def account_security(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("security")

    login_with_email = request.POST.get("login_with_email") == "on"

    try:
        user = request.user
        if user.login_with_email == login_with_email:
            messages.warning(request, "There were no changes")
            return redirect_with_tab("security")

        user.login_with_email = login_with_email
        user.save()
        messages.success(request, "Successfully updated security settings")
        return redirect_with_tab("security")
    except Exception as e:
        messages.error(request, f"Error updating security settings: {e}")
        return redirect_with_tab("security")


@login_required
def change_password(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("security")

    old_password = request.POST.get("old_password") or ""
    new_password = request.POST.get("new_password") or ""

    try:
        if not validate([old_password, new_password]):
            bad_request_error("Please fill in all fields")
        if old_password.strip() == new_password.strip():
            bad_request_error("The old and new password cannot be the same")

        user = request.user
        if not user.email_verified:
            bad_request_error("Please verify your email first")
        if not user.check_password(old_password):
            bad_request_error("The old password is incorrect")

        password_id_valid = validate_password(new_password)
        if not password_id_valid[0]:
            bad_request_error(password_id_valid[1])

        user.set_password(new_password)
        user.save()
        send_password_changed_email.delay_on_commit(request.user.id)
        messages.success(request, "Successful updated password! Please re-login")
        return redirect_with_tab("security")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("security")
    except Exception as e:
        messages.error(request, f"Error updating password: {e}")
        return redirect_with_tab("security")


@login_required
def resend_verify_email(request: HttpRequest):
    try:
        user = request.user
        if user.email_verified:
            bad_request_error("Email has already been verified")
        send_email_verification.delay_on_commit(user.id)
        messages.success(request, "Verification email sent successfully")
        return redirect_with_tab("email")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("email")
    except Exception as e:
        messages.error(request, f"Error sending verification email: {e}")
        return redirect_with_tab("email")


@login_required
def delete_account(request: HttpRequest):
    if request.method != "POST":
        return redirect("my_account")

    user = request.user
    try:
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not user.email_verified:
            bad_request_error("Please verify your email first")

        if not validate([username, password]):
            bad_request_error("Please fill in all fields")
        if user.username != username or not user.check_password(password):
            bad_request_error("Incorrect username or password")

        user_email = user.email
        send_deleted_account_email.delay_on_commit(user_email, username)
        user.delete()
        messages.success(request, "Account deleted successfully")
        return redirect("sign_in")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect("my_account")
    except Exception as e:
        messages.error(request, f"Error deleting account: {e}")
        return redirect("my_account")


def set_user_timezone(request: HttpRequest):
    if "timezone" in request.POST:
        request.session["user_timezone"] = request.POST["timezone"]
    return JsonResponse({"status": "ok"})
