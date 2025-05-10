import contextlib
import logging
from datetime import datetime
from decimal import Decimal

from django.utils.timezone import now
from stripe import Customer
from stripe import Event
from stripe import Invoice
from stripe import Subscription as StripeSubscription

from sbily.users.models import User

from .models import Payment
from .models import Subscription

logger = logging.getLogger("payments.webhook")


# Webhook handler for Stripe events
def handle_stripe_webhook(event: Event):
    """Handle Stripe webhook events"""
    event_type = event.type

    if event_type == "invoice.payment_succeeded":
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


def handle_invoice_payment_succeeded(invoice: Invoice):
    """Handle successful invoice payment"""
    subscription_details = invoice.parent.subscription_details
    if stripe_subscription_id := subscription_details.subscription:
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            payment_description = (
                f"Monthly Premium Subscription - Invoice {invoice.number}"
            )

            # Create payment record if doesn't exist
            payment, created = Payment.objects.get_or_create(
                transaction_id=invoice.id,
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.get("amount_paid", 0))
                    / 100,  # Convert from cents
                    "description": payment_description,
                    "status": Payment.STATUS_COMPLETED,
                    "transaction_id": invoice.id,
                },
            )

            if not created:
                payment.description = payment_description
                payment.complete()
                subscription.renew()

            # Update subscription status
            subscription.status = Subscription.STATUS_ACTIVE
            period_end = invoice.lines.data[0].period.end
            subscription.end_date = datetime.fromtimestamp(period_end, tz=now().tzinfo)
            subscription.save()
            subscription.user.reset_monthly_link_limit()


def handle_invoice_payment_failed(invoice: Invoice):
    """Handle failed invoice payment"""
    subscription_details = invoice.parent.subscription_details
    if stripe_subscription_id := subscription_details.subscription:
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            # Create payment record if doesn't exist
            payment, _ = Payment.objects.get_or_create(
                transaction_id=invoice.id,
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.get("amount_due", 0))
                    / 100,  # Convert from cents
                    "description": "Failed Monthly Premium Subscription",
                    "status": Payment.STATUS_FAILED,
                },
            )

            payment.fail("Invoice payment failed")
            subscription.cancel_stripe_subscription_immediately()


def handle_invoice_payment_action_required(invoice: Invoice):
    """Handle invoice payment action required"""
    subscription_details = invoice.parent.subscription_details
    if stripe_subscription_id := subscription_details.subscription:
        with contextlib.suppress(Subscription.DoesNotExist):
            subscription = Subscription.objects.get(
                stripe_subscription_id=stripe_subscription_id,
            )

            # Create payment record if doesn't exist
            payment, _ = Payment.objects.get_or_create(
                transaction_id=invoice.id,
                defaults={
                    "user": subscription.user,
                    "amount": Decimal(invoice.amount_due or 0)
                    / 100,  # Convert from cents
                    "description": f"Monthly Premium Subscription - Invoice {invoice.number}",  # noqa: E501
                    "status": Payment.STATUS_PENDING,
                },
            )

            payment.status = Payment.STATUS_PENDING
            payment.save()
            subscription.status = Subscription.STATUS_INCOMPLETE
            subscription.save()


def handle_subscription_created(subscription_obj: StripeSubscription):
    """Handle subscription created event"""
    if customer_id := subscription_obj.customer:
        with contextlib.suppress(User.DoesNotExist):
            data = subscription_obj.get("items", {}).data[0]
            user = User.objects.get(stripe_customer_id=customer_id)

            period_end = data.current_period_end
            current_period_end = datetime.fromtimestamp(period_end, tz=now().tzinfo)
            is_auto_renew = not subscription_obj.cancel_at_period_end

            # Create subscription if it doesn't exist
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    "stripe_subscription_id": subscription_obj.id,
                    "status": Subscription.STATUS_ACTIVE,
                    "start_date": now(),
                    "end_date": current_period_end,
                    "is_auto_renew": is_auto_renew,
                    "price": Decimal(data.plan.amount or 0) / 100,  # Convert from cents
                },
            )

            if not created:
                subscription.stripe_subscription_id = subscription_obj.id
                subscription.end_date = current_period_end
                subscription.is_auto_renew = is_auto_renew
                subscription.status = Subscription.STATUS_ACTIVE
                subscription.save()

            user.upgrade_to_premium()


def handle_subscription_updated(subscription_obj: Subscription):
    """Handle subscription updated event"""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_obj.id,
        )
        subscription.update_from_stripe(stripe_sub=subscription_obj)
    except Subscription.DoesNotExist:
        # Handle new subscription that was created directly in Stripe
        handle_subscription_created(subscription_obj)


def handle_subscription_deleted(subscription_obj: Subscription):
    """Handle subscription deleted event"""
    with contextlib.suppress(Subscription.DoesNotExist):
        subscription = Subscription.objects.get(
            stripe_subscription_id=subscription_obj.id,
        )
        subscription.cancel()
        subscription.user.downgrade_to_free()


def handle_customer_updated(customer: Customer):
    """Handle customer updated event"""
    if customer_id := customer.id:
        try:
            user = User.objects.get(stripe_customer_id=customer_id)
            user.update_card_details(
                customer.invoice_settings.default_payment_method or None,
            )
        except User.DoesNotExist:
            logger.warning(
                "Customer updated event received for non-existent user: %s",
                customer_id,
                exc_info=True,
            )
