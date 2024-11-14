import logging
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from app.tasks import send_email
from django.urls import reverse
from subscriptions.models import UserSubscription, SubscriptionPlan
User = get_user_model()


logger = logging.getLogger(__name__)
@receiver(post_save, sender=User)
def send_welcome_email(sender, instance, created, **kwargs):
    if created:
        subject = "Welcome to Testimonials"
        template_path = "emails/test"   
        receiver = [instance.email]
        
        merge_data = {
                    "user_name": instance.first_name, 
                    
                }
        try:
                send_email.delay(subject, template_path, receiver, merge_data)
                logger.info("Sent welcome email to user: %s", instance.email)
        except Exception as e:
                logger.error("Failed to send welcome email to user: %s", instance.email, exc_info=True)


@receiver(post_save, sender=User)
def enroll_subscription(sender, instance, created, **kwargs):
    if created:

        try:
            basic_plan = SubscriptionPlan.objects.get(access_level=1)
        except SubscriptionPlan.DoesNotExist:
            return None

        UserSubscription.objects.create(
            user= instance, 
            plan=basic_plan

        )
