# ruff: noqa: BLE001

import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import now
from django.utils.timezone import timedelta
from django.views.decorators.csrf import csrf_exempt

from sbily.utils.data import validate
from sbily.utils.data import validate_password
from sbily.utils.errors import BadRequestError
from sbily.utils.errors import bad_request_error
from sbily.utils.urls import redirect_with_params

from .forms import ProfileForm
from .models import Subscription
from .models import Token
from .models import User
from .tasks import send_deleted_account_email
from .tasks import send_email_change_instructions
from .tasks import send_email_changed_email
from .tasks import send_email_verification
from .tasks import send_password_changed_email
from .webhook import handle_stripe_webhook

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger("users.views")


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


@login_required
def upgrade_plan(request: HttpRequest):
    if request.method != "GET":
        return redirect_with_tab("plan")

    try:
        user = request.user
        if user.is_premium:
            bad_request_error("You are already a premium user")

        customer = user.get_stripe_customer()
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["card"],
        )

        return render(
            request,
            "payment/setup_card.html",
            {
                "client_secret": setup_intent.client_secret,
                "redirect_url": request.build_absolute_uri(
                    reverse("finalize_upgrade"),
                ),
            },
        )

    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("plan")
    except stripe.error.StripeError as e:
        messages.error(request, f"Payment error: {e!s}")
        return redirect_with_tab("plan")


@login_required
def finalize_upgrade(request: HttpRequest):
    """Handle the redirect after card setup for upgrade"""
    if request.method != "GET":
        return redirect_with_tab("plan")

    payment_method = request.GET.get("payment_method")
    setup_intent = request.GET.get("setup_intent")

    if not validate([payment_method, setup_intent]):
        messages.error(request, "Missing payment information")
        return redirect_with_tab("plan")

    try:
        user = request.user
        if user.is_premium:
            bad_request_error("You are already a premium user")

        subscription, _ = Subscription.objects.get_or_create(
            user=user,
            defaults={
                "price": 5.00,  # Monthly premium price
                "status": Subscription.STATUS_INCOMPLETE,
                "start_date": now(),
                "end_date": now() + timedelta(days=30),
                "is_auto_renew": True,
            },
        )

        # Create Stripe subscription
        result = subscription.create_stripe_subscription(
            payment_method_id=payment_method,
        )

        if result["status"] == "success":
            user.upgrade_to_premium()
            messages.success(request, "Successfully upgraded to premium!")
            return redirect_with_tab("plan")
        if result["status"] == "action_required":
            return render(
                request,
                "payment/confirm_payment.html",
                {
                    "client_secret": result["client_secret"],
                    "redirect_url": request.build_absolute_uri(
                        reverse("subscription_complete"),
                    ),
                },
            )
        subscription.delete()  # Clean up failed subscription
        messages.error(
            request,
            f"Payment failed: {result.get('error', 'Unknown error')}",
        )
        return redirect_with_tab("plan")

    except Exception as e:
        messages.error(request, f"Error processing upgrade: {e!s}")
        return redirect_with_tab("plan")


@login_required
def subscription_complete(request: HttpRequest):
    """Handle completion of subscription payment"""
    if request.method != "GET":
        return redirect_with_tab("plan")

    payment_intent = request.GET.get("payment_intent")

    if not payment_intent:
        messages.error(request, "Missing payment information")
        return redirect_with_tab("plan")

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent)

        if intent.status == "succeeded":
            user = request.user
            user.upgrade_to_premium()
            messages.success(request, "Successfully upgraded to premium!")
        else:
            messages.error(request, f"Payment not completed: {intent.status}")

        return redirect_with_tab("plan")
    except stripe.error.StripeError as e:
        messages.error(request, f"Payment verification error: {e!s}")
        return redirect_with_tab("plan")


@login_required
def downgrade_plan(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user = request.user
        if not user.is_premium:
            bad_request_error("You are not a premium user")

        subscription = Subscription.objects.filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
        ).first()

        if subscription and subscription.stripe_subscription_id:
            result = subscription.cancel_stripe_subscription()
            if result["status"] != "success":
                messages.warning(
                    request,
                    f"Warning: Stripe cancellation issue - {result.get('error')}",
                )

        # Proceed with downgrade anyway
        if message := user.downgrade_to_free():
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
def purchase_links(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user = request.user
        if not user.is_premium:
            bad_request_error(
                "You need to be a premium user to purchase additional links",
            )

        customer = user.get_stripe_customer()
        if not customer.invoice_settings.default_payment_method:
            messages.error(request, "Please add a payment method first")
            return add_payment_method(request)

        link_type = request.POST.get("link_type")
        quantity = int(request.POST.get("quantity", 0))

        if not link_type or quantity <= 0:
            bad_request_error("Invalid link type or quantity")

        if link_type not in ["permanent", "temporary"]:
            bad_request_error("Invalid link type")

        result = user.process_package_payment(
            link_type=link_type,
            quantity=quantity,
        )

        if result["status"] == "success":
            messages.success(
                request,
                f"Successfully purchased {quantity} {link_type} links!",
            )
        elif result["status"] == "action_required":
            return render(
                request,
                "payment/confirm_payment.html",
                {
                    "client_secret": result["client_secret"],
                    "redirect_url": request.build_absolute_uri(
                        reverse("purchase_complete"),
                    ),
                },
            )
        else:
            messages.error(
                request,
                f"Payment failed: {result.get('error', 'Unknown error')}",
            )
    except BadRequestError as e:
        messages.error(request, e.message)
    except Exception as e:
        messages.error(request, f"Error purchasing links: {e!s}")

    return redirect_with_tab("plan")


@login_required
def add_payment_method(request: HttpRequest):
    """Add a new payment method to the user's account"""
    try:
        user = request.user

        customer = user.get_stripe_customer()
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["card"],
        )

        return render(
            request,
            "payment/setup_card.html",
            {
                "client_secret": setup_intent.client_secret,
                "redirect_url": request.build_absolute_uri(
                    reverse("payment_method_added"),
                ),
            },
        )
    except Exception as e:
        messages.error(request, f"Error setting up payment method: {e!s}")
        return redirect_with_tab("plan")


@login_required
def payment_method_added(request: HttpRequest):
    """Handle redirect after adding payment method"""
    if payment_method := request.GET.get("payment_method"):
        try:
            user = request.user

            # Attach payment method to customer
            customer = user.get_stripe_customer()
            stripe.PaymentMethod.attach(
                payment_method,
                customer=customer.id,
            )

            stripe.Customer.modify(
                customer.id,
                invoice_settings={
                    "default_payment_method": payment_method,
                },
            )

            user.update_card_details(payment_method)
            messages.success(request, "Payment method successfully added!")
        except Exception as e:
            messages.error(request, f"Error adding payment method: {e!s}")

    return redirect_with_tab("plan")


@login_required
def purchase_complete(request: HttpRequest):
    """Handle completion of link purchase payment"""
    if request.method != "GET":
        return redirect_with_tab("plan")

    payment_intent = request.GET.get("payment_intent")

    if not payment_intent:
        messages.error(request, "Missing payment information")
        return redirect_with_tab("plan")

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent)

        if intent.status == "succeeded":
            metadata = intent.metadata
            link_type = metadata.get("package_type")
            quantity = int(metadata.get("quantity", 0))

            if link_type and quantity > 0:
                messages.success(
                    request,
                    f"Successfully purchased {quantity} {link_type} links!",
                )
            else:
                messages.success(request, "Payment completed successfully!")
        else:
            messages.error(request, f"Payment not completed: {intent.status}")

        return redirect_with_tab("plan")
    except stripe.error.StripeError as e:
        messages.error(request, f"Payment verification error: {e!s}")
        return redirect_with_tab("plan")


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    try:
        handle_stripe_webhook(event)
        return JsonResponse({"status": "success"})
    except Exception as e:
        logger.exception("Error handling Stripe webhook", exc_info=e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
