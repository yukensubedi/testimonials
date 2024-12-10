import stripe
import logging
from . models import UserSubscription, SubscriptionPlan, Payment
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger('app')

def get_or_create_stripe_price(plan):
    """
    Retrieves or creates a Stripe Price for the given plan.
    """
     
    if plan.stripe_price_id:
        return plan.stripe_price_id

    price = stripe.Price.create(
        currency="usd",
        unit_amount_decimal=plan.price * 100,
        recurring={"interval": "month"},
        product_data={"name": plan.name},
    )
    plan.stripe_price_id = price['id']
    plan.save()
    return plan.stripe_price_id
def get_or_create_stripe_customer(user):
    """
    Retrieves or creates a Stripe customer for the given user.
    Ensures a UserSubscription object exists for the user.
    """
    stripe_customer, created = UserSubscription.objects.get_or_create(user=user, is_active=True)

    if stripe_customer.stripe_customer_id:
        return stripe_customer.stripe_customer_id

    customer = stripe.Customer.create(email=user.email)
    stripe_customer.stripe_customer_id = customer.id
    stripe_customer.save()

    return stripe_customer.stripe_customer_id


def handle_payment_success(invoice):
    stripe_customer_id = invoice['customer']
    stripe_subscription_id = invoice['subscription']
    amount_paid = invoice['amount_paid'] / 100  # Convert cents to dollars
    transaction_id = invoice['id']

    # Get user and plan
    user_subscription = UserSubscription.objects.filter(stripe_customer_id=stripe_customer_id, is_active=True).first()
    user = user_subscription.user if user_subscription else None
    if not user:
        return  # Handle edge case: No active subscription found

    stripe_plan_id = invoice['lines']['data'][0]['price']['id']
    plan = SubscriptionPlan.objects.filter(stripe_price_id=stripe_plan_id).first()

    # Create Payment record
    Payment.objects.create(
        user=user,
        product_uuid=stripe_plan_id,
        amount=amount_paid,
        transaction_id=transaction_id,
        status='completed',
        stripe_subscription_id=stripe_subscription_id,
    )

    # Deactivate any currently active subscriptions
    UserSubscription.deactivate_active_subscriptions(user)

    # Create a new subscription entry
    UserSubscription.objects.create(
        user=user,
        plan=plan,
        stripe_customer_id=stripe_customer_id,
        start_date=timezone.now(),
        end_date=timezone.now() + timedelta(days=plan.duration_days),
        is_active=True,
    )
def handle_payment_failure(invoice):
    try:
        stripe_customer_id = invoice['customer']
        print(stripe_customer_id)
        transaction_id = invoice['id']
        stripe_subscription_id = invoice['subscription']
        amount_paid = invoice['amount_due'] / 100  # Convert cents to dollars

        print(stripe_subscription_id, transaction_id, amount_paid)
        
        # Ensure UserSubscription exists and get user
        user_subscription = UserSubscription.objects.filter(stripe_customer_id=stripe_customer_id).first()
        if not user_subscription:
            print(f"No UserSubscription found for Stripe customer ID: {stripe_customer_id}")
        
        user = user_subscription.user
        print(user)

        # Update Payment entry to failed
        Payment.objects.create(
            user=user,
            product_uuid=stripe_subscription_id,
            amount=amount_paid,
            transaction_id=transaction_id,
            status='failed',
            stripe_subscription_id=stripe_subscription_id,
        )
        print("Payment failure handled successfully.")
    
    except Exception as e:
        print(f"Error handling payment failure: {e}")
