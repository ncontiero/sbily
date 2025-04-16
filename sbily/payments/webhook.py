import contextlib
import logging
from datetime import datetime
from decimal import Decimal

from django.utils.timezone import now
from stripe import Event

from sbily.users.models import User

from .models import LinkPackage
from .models import Payment
from .models import Subscription

logger = logging.getLogger("payments.webhook")


# Webhook handler for Stripe events
def handle_stripe_webhook(event: Event):
    """Handle Stripe webhook events"""
    event_type = event.type

    if event_type == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        handle_payment_intent_succeeded(payment_intent)

    elif event_type == "payment_intent.payment_failed":
        payment_intent = event["data"]["object"]
        handle_payment_intent_failed(payment_intent)

    elif event_type == "invoice.payment_succeeded":
        invoice = event["data"]["object"]
        handle_invoice_payment_succeeded(invoice)

    elif event_type == "invoice.payment_action_required":
        invoice = event["data"]["object"]
        handle_invoice_payment_action_required(invoice)

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        handle_invoice_payment_failed(invoice)

    elif event_type == "customer.subscription.created":
        subscription = event["data"]["object"]
        handle_subscription_created(subscription)

    elif event_type == "customer.subscription.updated":
        subscription = event["data"]["object"]
        handle_subscription_updated(subscription)

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        handle_subscription_deleted(subscription)

    elif event_type == "customer.updated":
        customer = event["data"]["object"]
        handle_customer_updated(customer)

    return {"status": "success", "event_type": event_type}


def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent"""
    with contextlib.suppress(Payment.DoesNotExist):
        payment = Payment.objects.get(transaction_id=payment_intent["id"])
        payment.complete(transaction_id=payment_intent["id"])

        if payment.payment_type == Payment.TYPE_PACKAGE:
            metadata = payment_intent.get("metadata", {})
            package_type = metadata.get("package_type")
            quantity = int(metadata.get("quantity", 0))

            if package_type and quantity > 0:
                user = payment.user

                LinkPackage.objects.create(
                    user=user,
                    link_type=package_type,
                    quantity=quantity,
                    unit_price=payment.amount / quantity,
                    payment=payment,
                )

                if package_type == LinkPackage.TYPE_PERMANENT:
                    user.max_num_links += quantity
                else:
                    user.max_num_links_temporary += quantity
                user.save(update_fields=["max_num_links", "max_num_links_temporary"])


def handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent"""
    with contextlib.suppress(Payment.DoesNotExist):
        payment = Payment.objects.get(transaction_id=payment_intent["id"])
        payment.fail(
            f"Payment failed: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}",  # noqa: E501
        )


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    if stripe_subscription_id := invoice.get("subscription"):
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            payment_description = (
                f"Monthly Premium Subscription - Invoice {invoice.get('number')}"
            )

            # Create payment record if doesn't exist
            payment, created = Payment.objects.get_or_create(
                transaction_id=invoice.get("id"),
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.get("amount_paid", 0))
                    / 100,  # Convert from cents
                    "description": payment_description,
                    "payment_type": Payment.TYPE_SUBSCRIPTION,
                    "status": Payment.STATUS_COMPLETED,
                    "transaction_id": invoice.get("id"),
                },
            )

            if not created:
                payment.description = payment_description
                payment.complete()
                subscription.renew()

            # Update subscription status
            subscription.status = Subscription.STATUS_ACTIVE
            period_end = (
                invoice.get("lines", {})
                .get("data", [])[0]
                .get(
                    "period",
                    {},
                )
                .get("end")
            )
            subscription.end_date = datetime.fromtimestamp(period_end, tz=now().tzinfo)
            subscription.save()


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    if stripe_subscription_id := invoice.get("subscription"):
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            # Create payment record if doesn't exist
            payment, _ = Payment.objects.get_or_create(
                transaction_id=invoice.get("id"),
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.get("amount_due", 0))
                    / 100,  # Convert from cents
                    "description": "Failed Monthly Premium Subscription",
                    "payment_type": Payment.TYPE_SUBSCRIPTION,
                    "status": Payment.STATUS_FAILED,
                },
            )

            payment.fail("Invoice payment failed")
            subscription.cancel_stripe_subscription_immediately()


def handle_invoice_payment_action_required(invoice):
    """Handle invoice payment action required"""
    if stripe_subscription_id := invoice.get("subscription"):
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            # Create payment record if doesn't exist
            payment, _ = Payment.objects.get_or_create(
                transaction_id=invoice.get("id"),
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.get("amount_due", 0))
                    / 100,  # Convert from cents
                    "description": f"Monthly Premium Subscription - Invoice {invoice.get('number')}",  # noqa: E501
                    "payment_type": Payment.TYPE_SUBSCRIPTION,
                    "status": Payment.STATUS_PENDING,
                },
            )

            payment.status = Payment.STATUS_PENDING
            payment.save()
            subscription.status = Subscription.STATUS_INCOMPLETE
            subscription.save()


def handle_subscription_created(subscription_obj):
    """Handle subscription created event"""
    if customer_id := subscription_obj.get("customer"):
        with contextlib.suppress(User.DoesNotExist):
            user = User.objects.get(stripe_customer_id=customer_id)

            current_period_end = datetime.fromtimestamp(
                subscription_obj.get("current_period_end"),
                tz=now().tzinfo,
            )
            is_auto_renew = not subscription_obj.get("cancel_at_period_end", False)

            # Create subscription if it doesn't exist
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    "stripe_subscription_id": subscription_obj.get("id"),
                    "status": Subscription.STATUS_ACTIVE,
                    "start_date": now(),
                    "end_date": current_period_end,
                    "is_auto_renew": is_auto_renew,
                    "price": Decimal(subscription_obj.get("plan", {}).get("amount", 0))
                    / 100,  # Convert from cents
                },
            )

            if not created:
                subscription.stripe_subscription_id = subscription_obj.get("id")
                subscription.end_date = current_period_end
                subscription.is_auto_renew = is_auto_renew
                subscription.save()

            user.upgrade_to_premium()


def handle_subscription_updated(subscription_obj):
    """Handle subscription updated event"""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_obj.get("id"),
        )
        subscription.update_from_stripe(stripe_sub=subscription_obj)
    except Subscription.DoesNotExist:
        # Handle new subscription that was created directly in Stripe
        handle_subscription_created(subscription_obj)


def handle_subscription_deleted(subscription_obj):
    """Handle subscription deleted event"""
    with contextlib.suppress(Subscription.DoesNotExist):
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_obj.get("id"),
        )
        subscription.cancel()
        subscription.user.downgrade_to_free()


def handle_customer_updated(customer_obj):
    """Handle customer updated event"""
    if customer_id := customer_obj.get("id"):
        try:
            user = User.objects.get(stripe_customer_id=customer_id)
            user.update_card_details(
                customer_obj.invoice_settings.default_payment_method or None,
            )
        except User.DoesNotExist:
            logger.warning(
                "Customer updated event received for non-existent user: %s",
                customer_id,
                exc_info=True,
            )
