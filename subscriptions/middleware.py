from django.shortcuts import redirect
from django.urls import reverse
from .models import UserSubscription

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Retrieve the active subscription for the user
                subscription = UserSubscription.objects.filter(user=request.user, is_active=True).first()
                request.subscription = subscription
            except UserSubscription.DoesNotExist:
                request.subscription = None

        response = self.get_response(request)
        return response