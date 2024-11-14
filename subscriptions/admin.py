from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription
import json

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'price', 'duration_days', 'access_level')
    list_filter = ('access_level',)
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'price', 'duration_days', 'access_level', 'feature_limits')
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
    list_filter = ('plan', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__email', 'plan__name')
    readonly_fields = ('is_active',)

    def is_active(self, obj):
        return obj.is_active()
    is_active.boolean = True
    is_active.short_description = 'Is Active'

    fieldsets = (
        (None, {
            'fields': ('user', 'plan', 'start_date', 'end_date')
        }),
    )
