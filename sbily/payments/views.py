import logging
from typing import TYPE_CHECKING

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from sbily.utils.data import validate
from sbily.utils.errors import BadRequestError
from sbily.utils.errors import bad_request_error
from sbily.utils.urls import redirect_with_tab

if TYPE_CHECKING:
    from sbily.users.models import User

from .models import Subscription
from .utils import PlanCycle
from .utils import PlanType
from .utils import validate_plan_selection
from .webhook import handle_stripe_webhook

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger("users.views")


@login_required
def upgrade_plan(request: HttpRequest):
    if request.method != "GET":
        return redirect_with_tab("plan")

    plan = request.GET.get("plan", PlanType.PREMIUM.value)
    plan_cycle = request.GET.get("cycle", PlanCycle.MONTHLY.value)

    try:
        user: User = request.user
        validate_plan_selection(plan, plan_cycle, user)

        customer = user.get_stripe_customer()
        default_payment_method = customer.invoice_settings.default_payment_method

        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["card"],
        )

        context = {
            "client_secret": setup_intent.client_secret,
            "redirect_url": request.build_absolute_uri(reverse("finalize_upgrade")),
            "plan": plan,
            "plan_cycle": plan_cycle,
            "default_payment_method": default_payment_method,
        }
        return render(request, "upgrade.html", context)
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("plan")
    except stripe.error.StripeError as e:
        messages.error(request, "Payment error")
        logger.exception("Stripe error", exc_info=e)
        return redirect_with_tab("plan")


@login_required
def finalize_upgrade(request: HttpRequest):
    """Handle the redirect after card setup for upgrade"""
    if request.method != "GET":
        return redirect_with_tab("plan")

    payment_method = request.GET.get("payment_method")
    plan = request.GET.get("plan", PlanType.PREMIUM.value)
    plan_cycle = request.GET.get("plan_cycle", PlanCycle.MONTHLY.value)

    if not validate([payment_method]):
        messages.error(request, "Missing payment information")
        return redirect_with_tab("plan")

    try:
        user: User = request.user
        validate_plan_selection(plan, plan_cycle, user)

        result = Subscription.create_subscription(
            user,
            payment_method,
            plan,
            plan_cycle,
        )

        if result["status"] == "success":
            user.choose_plan(plan)
            messages.success(request, f"Successfully upgraded to {plan}!")
            return redirect_with_tab("plan")
        if result["status"] == "action_required":
            return render(
                request,
                "confirm_payment.html",
                {
                    "client_secret": result["client_secret"],
                    "redirect_url": request.build_absolute_uri(
                        reverse("subscription_complete"),
                    ),
                },
            )
        messages.error(
            request,
            f"Payment failed: {result.get('error', 'Unknown error')}",
        )
        return redirect_with_tab("plan")

    except Exception as e:
        messages.error(request, "Error processing upgrade")
        logger.exception("Error processing upgrade", exc_info=e)
        return redirect_with_tab("plan")


@login_required
def subscription_complete(request: HttpRequest):
    """Handle completion of subscription payment"""
    if request.method != "GET":
        return redirect_with_tab("plan")

    plan = request.GET.get("plan", PlanType.PREMIUM.value)
    payment_intent = request.GET.get("payment_intent")

    if not payment_intent:
        messages.error(request, "Missing payment information")
        return redirect_with_tab("plan")

    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent)

        if intent.status == "succeeded":
            request.user.choose_plan(plan)
            messages.success(request, "Successfully upgraded to premium!")
        else:
            messages.error(request, f"Payment not completed: {intent.status}")

        return redirect_with_tab("plan")
    except stripe.error.StripeError as e:
        messages.error(request, "Payment verification error")
        logger.exception("Stripe error", exc_info=e)
        return redirect_with_tab("plan")


@login_required
def cancel_plan(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user: User = request.user
        if not user.subscription_active:
            bad_request_error("Your subscription is not active")

        subscription = Subscription.objects.filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
        ).first()

        if subscription and subscription.stripe_subscription_id:
            result = subscription.cancel_stripe_subscription()
            if result["status"] != "success":
                messages.warning(request, "Warning: Cancellation issue")
                logger.warning("Warning: Cancellation issue - %s", result.get("error"))
            else:
                messages.success(request, "Successfully canceled subscription!")

        return redirect_with_tab("plan")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("plan")
    except Exception as e:
        messages.error(request, "Error canceling subscription")
        logger.exception("Error canceling subscription", exc_info=e)
        return redirect_with_tab("plan")


@login_required
def resume_plan(request: HttpRequest):
    if request.method != "POST":
        return redirect_with_tab("plan")

    try:
        user: User = request.user
        if not user.subscription_active:
            bad_request_error("Your subscription is not active")
        if user.subscription_active and user.subscription.is_auto_renew:
            bad_request_error("Your subscription is already active")

        subscription = Subscription.objects.filter(
            user=user,
            status=Subscription.STATUS_ACTIVE,
        ).first()

        if subscription and subscription.stripe_subscription_id:
            result = subscription.resume_stripe_subscription()
            if result["status"] != "success":
                messages.warning(request, "Warning: Stripe resume issue")
                logger.warning("Warning: Stripe resume issue - %s", result.get("error"))
            else:
                messages.success(request, "Successfully resumed subscription!")

        return redirect_with_tab("plan")
    except BadRequestError as e:
        messages.error(request, e.message)
        return redirect_with_tab("plan")
    except Exception as e:
        messages.error(request, "Error resuming subscription")
        logger.exception("Error resuming subscription", exc_info=e)
        return redirect_with_tab("plan")


@login_required
def add_payment_method(request: HttpRequest):
    """Add a new payment method to the user's account"""
    try:
        customer = request.user.get_stripe_customer()
        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["card"],
        )

        return render(
            request,
            "setup_card.html",
            {
                "client_secret": setup_intent.client_secret,
                "redirect_url": request.build_absolute_uri(
                    reverse("payment_method_added"),
                ),
            },
        )
    except Exception as e:
        messages.error(request, "Error setting up payment method")
        logger.exception("Error setting up payment method", exc_info=e)
        return redirect_with_tab("billing")


@login_required
def payment_method_added(request: HttpRequest):
    """Handle redirect after adding payment method"""
    if payment_method := request.GET.get("payment_method"):
        try:
            user = request.user
            user.update_card_details(payment_method)
            messages.success(request, "Payment method successfully added!")
        except Exception as e:
            messages.error(request, "Error adding payment method")
            logger.exception("Error adding payment method", exc_info=e)

    return redirect_with_tab("billing")


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
    except ValueError as e:
        logger.exception("Invalid Stripe webhook payload", exc_info=e)
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.exception("Invalid Stripe webhook signature", exc_info=e)
        return HttpResponse(status=400)

    try:
        handle_stripe_webhook(event)
        return JsonResponse({"status": "success"})
    except Exception as e:
        logger.exception("Error handling Stripe webhook", exc_info=e)
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
