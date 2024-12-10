from django.urls import path
from .views import PricingPageView, create_checkout_session, stripe_webhook, PaymentListView

urlpatterns = [
    path('pricing', PricingPageView.as_view(), name='pricing'),

    path('create-checkout-session/', create_checkout_session, name='create_checkout_session'),
    # path('stripe/webhook/', stripe_webhook, name='stripe_webhook'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('payments/', PaymentListView.as_view(), name='payment_list'),
]
