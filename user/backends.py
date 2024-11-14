import logging
import requests
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from app.tasks import download_and_save_profile_image, send_email
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

User = get_user_model()

class GoogleAuthBackend(BaseBackend):
    def authenticate(self, request, token=None):
        """
        Authenticate user using a Google OAuth token.
        """
        if token is None:
            logger.error("No token provided for Google authentication.")
            return None

        # Verify the token with Google
        try:
            response = requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': token},
                timeout=5  # Timeout to handle unresponsive requests
            )
            response.raise_for_status()
        except RequestException as e:
            logger.error("Google token verification failed: %s", e)
            return None

        data = response.json()
        email = data.get('email')
        first_name = data.get('given_name')
        last_name = data.get('family_name', first_name)
        profile_image_url = data.get('picture')
        email_verified = data.get('email_verified', False).title()
        # Ensure email is present
        if not email:
            logger.error("Google token did not return an email.")
            return None

        # Get or create the user with Google data
        user, created = User.objects.get_or_create(
            email=email, defaults={
                "signup_method": "GOOGLE",
                "first_name": first_name,
                "last_name": last_name,
                "is_verified": email_verified
            }
        )

        if created and profile_image_url:
            logger.info("Created new user with email: %s", email)
            download_and_save_profile_image.delay(user.id, profile_image_url)
            logger.info("Triggered profile image download for user: %s", email)

        return user

    def get_user(self, user_id):
        """
        Retrieve user by ID, handling potential non-existence.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error("User with ID %s does not exist.", user_id)
            return None


