from django.contrib import admin
from .models import (
    OrphanForm, OrphanMother, OrphanFather,
    SpecialNeedsForm, FamilyForm, FamilyWife,
    CurrentGuardian, FamilyMember, Payment
)


@admin.register(OrphanForm)
class OrphanFormAdmin(admin.ModelAdmin):
    list_display  = ['form_number', 'get_full_name', 'status', 'sponsor', 'created_at']
    list_filter   = ['status']
    search_fields = ['form_number', 'first_name', 'family_name', 'id_number']
    readonly_fields = ['form_number', 'created_at', 'updated_at']


@admin.register(SpecialNeedsForm)
class SpecialNeedsFormAdmin(admin.ModelAdmin):
    list_display  = ['form_number', 'get_full_name', 'status', 'sponsor', 'created_at']
    list_filter   = ['status']
    search_fields = ['form_number', 'first_name', 'family_name', 'id_number']
    readonly_fields = ['form_number', 'created_at', 'updated_at']


@admin.register(FamilyForm)
class FamilyFormAdmin(admin.ModelAdmin):
    list_display  = ['form_number', 'get_full_name', 'status', 'sponsor', 'created_at']
    list_filter   = ['status']
    search_fields = ['form_number', 'first_name', 'family_name', 'id_number']
    readonly_fields = ['form_number', 'created_at', 'updated_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['beneficiary_type', 'beneficiary_id', 'sponsor',
                    'amount_shekel', 'payment_date', 'status']
    list_filter  = ['beneficiary_type', 'status', 'payment_date']