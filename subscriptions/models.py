import json
from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from user.models import AuditableModel


User = get_user_model()


class SubscriptionPlan(AuditableModel):
    name = models.CharField(max_length=50)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, null=True, blank=True)
    duration_days = models.IntegerField(default=30)  # Plan duration in days
    access_level = models.IntegerField()  # 1 for Starter, 2 for Pro, 3 for Premium
    feature_limits = models.JSONField(default=dict)  # e.g., {"max_details": 10, "analytics_access": False}

    def __str__(self):
        return self.name

    def get_limit(self, feature):
        """ Retrieve limit for a specific feature or return None if not specified """
        return self.feature_limits.get(feature)
    

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    stripe_customer_id = models.CharField(max_length=100, null=True, blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)  

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    @staticmethod
    def deactivate_active_subscriptions(user):
        """Deactivate all active subscriptions for a user."""
        UserSubscription.objects.filter(user=user, is_active=True).update(is_active=False)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"
    

class Payment(AuditableModel):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_uuid = models.CharField(max_length=100, null=True, blank=True, help_text='Identifier for the purchased product')
    amount = models.FloatField()
    transaction_id = models.CharField(max_length=100, unique=True)  # Stripe charge or invoice ID
    status = models.CharField(choices=PAYMENT_STATUS, max_length=20, default='pending')
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)  # Links to Stripe subscription
    description = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return f"Payment by {self.user.email} - {self.amount} ({self.status})"