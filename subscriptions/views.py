import stripe
import logging
import csv
from django.views.generic.base import TemplateView
from decouple import config
from django.http import HttpResponse
from .models import SubscriptionPlan, Payment
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt


from . helper import get_or_create_stripe_customer, get_or_create_stripe_price, handle_payment_failure, handle_payment_success
from .filters import PaymentFilter
from django_filters.views import FilterView

logger = logging.getLogger('app')

stripe.api_key = config('STRIPE_SECRET_KEY')

class PricingPageView(TemplateView):
    template_name = "subscriptions/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        plans = SubscriptionPlan.objects.order_by("access_level")  # Ensure plans are sorted
        user_subscription = getattr(self.request, "subscription", None)
        logger.info("Test for pricing")

        # Process the plans to include split descriptions
        for plan in plans:
            plan.features = [point.strip() for point in plan.description.split('.') if point.strip()]

        current_plan = user_subscription.plan if user_subscription else None

        context.update({
            "plans": plans,
            "current_plan": current_plan,
        })
        return context

@csrf_exempt 
@login_required
def create_checkout_session(request):
    """View to create a Stripe checkout session for subscriptions."""

    try:
        logger.info("Checkout session initiation started for user: %s", request.user.email)

        plan_name = request.GET.get('plan', '').title()
        return_url = request.GET.get('return_url', 'home')

        if not plan_name:
            messages.warning(request, "Error fetching the plan name.")
            logger.warning("No plan name provided by user: %s", request.user.email)
            return redirect(return_url)

        if plan_name == 'Free':
            logger.info("User %s selected the 'Free' plan. Redirecting to dashboard.", request.user.email)
            return redirect('dashboard')

        plan = get_object_or_404(SubscriptionPlan, name=plan_name)

        stripe_price_id = get_or_create_stripe_price(plan)
        logger.info("Stripe price ID for plan '%s': %s", plan_name, stripe_price_id)

        stripe_customer_id = get_or_create_stripe_customer(request.user)
        logger.info("Stripe customer ID for user %s: %s", request.user.email, stripe_customer_id)

        logger.info("Creating checkout session for user %s...", request.user.email)
        session = stripe.checkout.Session.create(
            mode='subscription',
            line_items=[{
                "price": stripe_price_id, 
                "quantity": 1
            }],
            metadata={
                "product_id": plan.id
            },
            success_url='http://127.0.0.1:8000/pricing',
            cancel_url='http://127.0.0.1:8000/',
            customer=stripe_customer_id,
        )
        logger.info("Checkout session created for user %s: %s", request.user.email, session.url)

        return HttpResponseRedirect(session.url)

    except stripe.error.StripeError as e:
        logger.error("Stripe error for user %s: %s", request.user.email, str(e))
        messages.warning(request, "There was an issue with Stripe. Please try again.")
        return redirect('home')

    except Exception as e:
        logger.exception("Unexpected error for user %s: %s", request.user.email, str(e))
        messages.warning(request, "An unexpected error occurred. Please contact support.")
        return redirect('home')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = config('STRIPE_WEBHOOK_SECRET')
    logger.info("Stripe webhook received. Verifying signature...")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        logger.info("Webhook verified successfully. Event type: %s", event['type'])
    except ValueError as e:
        logger.error("Invalid payload in Stripe webhook: %s", str(e))
        return HttpResponse("Invalid payload", status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error("Invalid signature in Stripe webhook: %s", str(e))
        return HttpResponse("Invalid signature", status=400)

    # Handle specific events
    try:
        if event['type'] == 'invoice.payment_succeeded':
            logger.info("Handling 'invoice.payment_succeeded' event for ID: %s", event['data']['object']['id'])
            handle_payment_success(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            logger.info("Handling 'invoice.payment_failed' event for ID: %s", event['data']['object']['id'])
            handle_payment_failure(event['data']['object'])
        else:
            logger.info("Unhandled event type: %s", event['type'])
    except Exception as e:
        logger.exception("Error handling Stripe webhook event: %s", str(e))
        return HttpResponse("Error processing webhook event", status=400)

    logger.info("Stripe webhook event processed successfully.")
    return HttpResponse(status=200)


class PaymentListView(LoginRequiredMixin, FilterView):
    """
    View to list and filter payments for the logged-in user with export functionality.
    """
    model = Payment
    template_name = "subscriptions/payment_history.html"  # Replace with your template path
    context_object_name = "payments"
    paginate_by = 10
    filterset_class = PaymentFilter

    def get_queryset(self):
        """
        Restrict queryset to the logged-in user's payments.
        """
        queryset = super().get_queryset()
        return queryset.filter(user=self.request.user).order_by('-created_at')

    def render_to_response(self, context, **response_kwargs):
        """
        Handle CSV export if the 'export' parameter is present in the GET request.
        """
        if "export" in self.request.GET:
            return self.export_to_csv(context['filter'].qs)
        return super().render_to_response(context, **response_kwargs)

    def export_to_csv(self, queryset):
        """
        Export filtered payments to CSV.
        """
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'

        writer = csv.writer(response)
        writer.writerow(['Transaction ID', 'Amount', 'Status', 'Product UUID', 'Date'])

        for payment in queryset:
            writer.writerow([
                payment.transaction_id,
                payment.amount,
                payment.get_status_display(),
                payment.product_uuid,
                payment.created_at,
            ])

        return response