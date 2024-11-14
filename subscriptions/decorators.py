from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps
from django.contrib import messages

def subscription_required(min_access_level, redirect_url='home'):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('sign_in')
            
            if not hasattr(request, 'subscription') or not request.subscription:
                messages.warning(request, 'Subscription required')
                return redirect('home')
            
            if request.subscription.plan.access_level < min_access_level:
                messages.warning(request, 'You are not allowed to perform this action. Please Upgrade')
                return redirect(redirect_url)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

