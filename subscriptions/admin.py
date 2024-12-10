from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, Payment
import json

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'duration_days', 'access_level', 'stripe_price_id')
    list_filter = ('access_level',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'price', 'stripe_price_id','duration_days', 'access_level', 'feature_limits')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def feature_limits_display(self, obj):
        return json.dumps(obj.feature_limits, indent=2)
    feature_limits_display.short_description = 'Feature Limits'

    # def get_readonly_fields(self, request, obj=None):
    #     if obj:  # Editing an existing object
    #         return self.readonly_fields + ('feature_limits',)
    #     return self.readonly_fields


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')
    list_filter = ('plan', 'start_date', 'end_date', 'is_active')
    search_fields = ('user__username', 'user__email', 'plan__name')


    fieldsets = (
        (None, {
            'fields': ('user', 'plan', 'start_date', 'end_date', 'stripe_customer_id', 'is_active')
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'transaction_id', 'status', 'stripe_subscription_id', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('user__email', 'transaction_id', 'stripe_subscription_id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('user', 'product_uuid', 'amount', 'transaction_id', 'status', 'stripe_subscription_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
    )