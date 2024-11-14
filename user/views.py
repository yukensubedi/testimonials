import os
import logging
import requests
from django.shortcuts import redirect
from django.contrib.auth import login, get_user_model, authenticate
from django.conf import settings
from django.views.generic.base import TemplateView
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy



User = get_user_model()


logger = logging.getLogger(__name__)

class HomeView(TemplateView):
    template_name = 'home.html'

class SignInView(TemplateView):
    template_name = 'login.html'

class LogoutView(LogoutView):
    next_page = reverse_lazy('home')
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have been successfully logged out.")
        return super().dispatch(request, *args, **kwargs)
    
def google_login(request):
    try:
        google_auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth"
            "?response_type=code"
            f"&client_id={settings.GOOGLE_CLIENT_ID}"
            f"&redirect_uri={settings.GOOGLE_REDIRECT_URI}"
            "&scope=openid email profile"
        )
        logger.info("Initiating Google login flow")
        return redirect(google_auth_url)
    except Exception as e:
        logger.error("Failed to initiate Google login", exc_info=True)
        messages.warning(request, "Unable to initiate Google login.")
        return redirect("home")

def google_callback(request):
    try:
        code = request.GET.get("code") 
        if not code:
            logger.warning("Google callback received without an authorization code")
            messages.warning(request, "Authentication failed")
            return redirect("home")

        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_data = token_response.json()
        id_token = token_data.get("id_token")

        if not id_token:
            logger.error("Google callback missing ID token in response")
            messages.warning(request, "Authentication failed")
            return redirect("home")

        user = authenticate(request, token=id_token)
        if user:
            login(request, user)
            logger.info(f"User {user.email} authenticated via Google successfully")
            return redirect("dashboard")
        else:
            logger.warning("Authentication failed for user with provided ID token")
            messages.warning(request, "Authentication failed")
            return redirect("home")

    except requests.RequestException as e:
        logger.error("Error during token exchange with Google", exc_info=True)
        messages.error(request, "Google authentication service is unavailable.")
        return redirect("home")
    except Exception as e:
        logger.error("Unexpected error in Google callback", exc_info=True)
        messages.error(request, "An unexpected error occurred.")
        return redirect("home")