from django.shortcuts import redirect
from django.urls import reverse
from .models import UserSubscription

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                subscription = UserSubscription.objects.get(user=request.user)
                if subscription.is_active():
                    request.subscription = subscription
                else:
                    request.subscription = None
            except UserSubscription.DoesNotExist:
                request.subscription = None

            # if not request.subscription and not request.path.startswith(reverse('subscription_required')):
            #     return redirect('subscription_required')

        response = self.get_response(request)
        return response