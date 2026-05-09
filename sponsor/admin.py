from django.contrib import admin
from .models import (SponsorProfile, PaymentReceipt,
                     PaymentSchedule, Message, Announcement)


@admin.register(SponsorProfile)
class SponsorProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'gender', 'nationality', 'job',
                     'can_contact', 'created_at']
    list_filter   = ['can_contact', 'gender']
    search_fields = ['user__username', 'user__first_name', 'user__family_name']


@admin.register(PaymentReceipt)
class PaymentReceiptAdmin(admin.ModelAdmin):
    list_display  = ['sponsor', 'receipt_date', 'amount_shekel',
                     'amount_dollar', 'unique_number', 'status', 'created_at']
    list_filter   = ['status', 'receipt_date']
    search_fields = ['sponsor__user__username', 'unique_number', 'sender_name']
    readonly_fields = ['created_at', 'reviewed_at']


@admin.register(PaymentSchedule)
class PaymentScheduleAdmin(admin.ModelAdmin):
    list_display  = ['sponsor', 'beneficiary_type', 'beneficiary_id',
                     'amount_shekel', 'due_day', 'is_active']
    list_filter   = ['beneficiary_type', 'is_active']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display  = ['title', 'target', 'is_active', 'created_at']
    list_filter   = ['target', 'is_active']