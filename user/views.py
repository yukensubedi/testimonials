import os
import requests
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import login, get_user_model, logout
from django.conf import settings
from django.core.files.base import ContentFile
from django.views.generic.base import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpRequest
from django.contrib import messages
from django.contrib.auth.views import LogoutView
from django.urls import reverse_lazy


User = get_user_model()

class HomeView(TemplateView):
    template_name = 'home.html'

class SignInView(TemplateView):
    template_name = 'signin.html'

class LogoutView(LogoutView):
    next_page = reverse_lazy('home')
    
    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "You have been successfully logged out.")
        return super().dispatch(request, *args, **kwargs)
    
@method_decorator(csrf_exempt, name='dispatch')
class AuthGoogleView(View):
    """
    Google calls this URL after the user has signed in with their Google account.
    """
    
    def post(self, request, *args, **kwargs):
        try:
            user_data = self.get_google_user_data(request)
        except ValueError as e:
            print(f"Token verification failed: {e}")
            return HttpResponse("Invalid Google token", status=403)

        print(user_data)
        email = user_data["email"]
        email = user_data.get('email')
        first_name = user_data.get('given_name', user_data.get('name', ''))
        last_name = user_data.get('family_name', first_name)  # Use 'first_name' as fallback if 'family_name' is missing
        email_verified = user_data.get('email_verified', False)
        profile_image_url = user_data.get('picture')

        if not email_verified:
            messages.error(request, 'Sign in Failed. Email is not verified')
            return redirect('sign_in')
        

        user, created =User.objects.get_or_create(
            email=email, defaults={
                "email": email,
                "signup_method": "GOOGLE",
                "first_name": first_name,
                "last_name": last_name,
                "is_verified": email_verified
            }
        )


        if created and profile_image_url:
            self.download_and_save_profile_image(user, profile_image_url)
        
            
        login(request, user)
        
        
        return redirect('dashboard')

    @staticmethod
    def get_google_user_data(request: HttpRequest):
        try:
            token = request.POST['credential']
            return id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID, 
                clock_skew_in_seconds=20
            )
        except Exception as e:
            raise ValueError("Google token verification failed", e) from e
        
    def download_and_save_profile_image(self, user, profile_image_url):
        try:
            response = requests.get(profile_image_url)
            if response.status_code == 200:
                image_name = f'{user.pk}_profile.jpg'
                user.profile_image.save(image_name, ContentFile(response.content), save=True)
        except Exception as e:
            print(f"Error downloading profile image: {e}")
       