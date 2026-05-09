from django.contrib import admin
from .models import (CustomUser, OTPVerification, OTPAttempt,
                     Notification, ActivityLog, Complaint, FAQ, SystemSettings)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display    = ['username', 'get_full_name', 'user_type',
                       'is_approved', 'is_active', 'login_count', 'date_joined']
    list_filter     = ['user_type', 'is_active', 'is_approved']
    search_fields   = ['username', 'email', 'id_number', 'first_name', 'family_name']
    readonly_fields = ['last_login_ip', 'login_count', 'last_seen', 'date_joined']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display    = ['user', 'action', 'description', 'ip_address', 'created_at']
    list_filter     = ['action']
    search_fields   = ['user__username', 'description']
    readonly_fields = ['user', 'action', 'description', 'ip_address', 'created_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'ntype', 'title', 'is_read', 'created_at']
    list_filter  = ['ntype', 'is_read']


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'subject', 'is_seen', 'is_replied', 'created_at']
    list_filter   = ['is_seen', 'is_replied']
    search_fields = ['name', 'email', 'subject']


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'target', 'order', 'is_active']
    list_filter  = ['target', 'is_active']


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display  = ['key', 'value', 'updated_at', 'updated_by']
    search_fields = ['key', 'value']
    readonly_fields = ['updated_at', 'updated_by']
    ordering      = ['key']