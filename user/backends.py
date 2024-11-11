# custom_auth_backend.py
import requests
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class GoogleAuthBackend(BaseBackend):
    def authenticate(self, request, token=None):
        if token is None:
            return None

        # Verify token with Google
        response = requests.get(
            'https://oauth2.googleapis.com/tokeninfo',
            params={'id_token': token}
        )
        if response.status_code != 200:
            return None

        data = response.json()
        email = data.get('email')
        first_name = data.get('given_name')
        last_name = data.get('family_name')

        if not email:
            return None

        # Get or create the user
        user, created = User.objects.get_or_create(email=email)
        if created:
            user.first_name = first_name
            user.last_name = last_name
            user.signup_method = 'GOOGLE'
            user.is_verified = True
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
