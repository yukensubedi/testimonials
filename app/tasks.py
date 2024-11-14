import os
import requests
import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from celery import shared_task
from smtplib import SMTPException
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile


User=get_user_model()

# Initialize the logger
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def send_email(self, subject, template_path, receiver=[], merge_data={}, file_path=None):
    """
    Sends an email with both text and HTML content, with optional attachment support.
    Retries up to 3 times in case of failure with a 5-minute delay between attempts.
    """

    try:
        # Render the email templates
        text_body = render_to_string(f"{template_path}.txt", merge_data)
        html_body = render_to_string(f"{template_path}.html", merge_data)
        
        # Create the email message
        msg = EmailMultiAlternatives(
            subject=subject,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=receiver,
            body=text_body
        )
        msg.attach_alternative(html_body, "text/html")

        # Attach file if provided
        if file_path:
            if os.path.isfile(file_path):
                file_name = os.path.basename(file_path)
                with open(file_path, 'rb') as f:
                    msg.attach(file_name, f.read())
                logger.debug("Attachment '%s' added successfully", file_name)
            else:
                logger.warning("Attachment '%s' does not exist, skipping attachment", file_path)

        # Send the email
        msg.send()
        logger.info("Email sent successfully to: %s", ", ".join(receiver))

    except SMTPException as e:
        logger.error("SMTP error occurred: %s", e)
        # Retry sending the email
        self.retry(exc=e)

    except Exception as e:
        logger.error("An unexpected error occurred while sending email: %s", e)
         


@shared_task
def download_and_save_profile_image(user_id, profile_image_url):
    """
    Download and save the profile image for the specified user asynchronously.
    """
    try:
        user = User.objects.get(pk=user_id)
        
        # Fetch the image from the URL
        response = requests.get(profile_image_url)
        
        if response.status_code == 200:
            image_name = f'{user.pk}_profile.jpg'
            user.profile_image.save(image_name, ContentFile(response.content), save=True)
            logger.info(f"Profile image saved for user {user.email}")
        else:
            logger.error(f"Failed to download image for user {user.email}: Status code {response.status_code}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist.")
    except Exception as e:
        logger.error(f"Error downloading profile image for user {user_id}: {e}")