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
    duration_days = models.IntegerField(default=30)  # Plan duration in days
    access_level = models.IntegerField()  # 1 for Starter, 2 for Pro, 3 for Premium
    feature_limits = models.JSONField(default=dict)  # e.g., {"max_details": 10, "analytics_access": False}

    def __str__(self):
        return self.name

    def get_limit(self, feature):
        """ Retrieve limit for a specific feature or return None if not specified """
        return self.feature_limits.get(feature)
    

class UserSubscription(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.plan.duration_days)
        super().save(*args, **kwargs)

    def is_active(self):
        return self.end_date > timezone.now()

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"