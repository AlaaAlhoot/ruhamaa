"""
admin_panel/views/search.py
البحث الموحد في النظام
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q

from core.models import CustomUser, Notification, Payment
from django.db.models import Sum
from django.utils import timezone
from .decorators import admin_required


def _build_result(user, user_type):
    """بناء بيانات مستخدم واحد للنتيجة"""
    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm
    from sponsor.models import SponsorProfile

    photo       = None
    sponsor_name= None
    status      = None

    model_map = {
        'orphan':  OrphanForm,
        'family':  FamilyForm,
        'special': SpecialNeedsForm,
    }

    Model = model_map.get(user_type)
    if Model:
        try:
            form = Model.objects.get(user=user)
            status = form.status
            if hasattr(form, 'photo') and form.photo:
                photo = form.photo.url
            if hasattr(form, 'sponsor') and form.sponsor:
                sponsor_name = form.sponsor.user.get_full_name()
        except Model.DoesNotExist:
            pass
    elif user_type == 'sponsor':
        try:
            sp = SponsorProfile.objects.get(user=user)
            if sp.photo:
                photo = sp.photo.url
        except SponsorProfile.DoesNotExist:
            pass

    return {
        'id':           str(user.pk),
        'full_name':    user.get_full_name(),
        'email':        user.email,
        'phone':        f'{user.phone_country}{user.phone}',
        'id_number':    user.id_number or '',
        'reg_number':   user.registration_number or '',
        'is_active':    user.is_active,
        'photo':        photo,
        'sponsor_name': sponsor_name,
        'status':       status,
        'date_joined':  user.date_joined.strftime('%Y/%m/%d'),
        'is_approved': user.is_approved,
    }


@admin_required
def search_view(request):
    notif_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    return render(request, 'admin_panel/unified_search.html', {
        'notif_count': notif_count,
    })


@admin_required
@require_GET
def search_data(request):
    q     = request.GET.get('q', '').strip()
    types = request.GET.get('types', 'orphan,family,special,sponsor').split(',')

    if len(q) < 2:
        return JsonResponse({'error': 'قصير جداً'}, status=400)

    results = {}

    # بناء فلتر البحث
    search_filter = (
        Q(first_name__icontains=q)      |
        Q(father_name__icontains=q)     |
        Q(grand_name__icontains=q)      |
        Q(family_name__icontains=q)     |
        Q(email__icontains=q)           |
        Q(id_number__icontains=q)       |
        Q(registration_number__icontains=q) |
        Q(phone__icontains=q)
    )

    base_qs = CustomUser.objects.filter(
        search_filter,
    ).exclude(user_type='admin')

    TYPE_MAP = {
        'orphan':  'orphan',
        'family':  'family',
        'special': 'special',
        'sponsor': 'sponsor',
    }

    for type_key, type_val in TYPE_MAP.items():
        if type_key not in types:
            continue
        users = base_qs.filter(user_type=type_val).order_by('-date_joined')[:20]
        results[f'{type_key}s'] = [_build_result(u, type_val) for u in users]

    return JsonResponse(results)
