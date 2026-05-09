from functools import wraps
from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone

from core.models import CustomUser, Notification, DirectMessage, Aid, Payment
from core.utils import log_activity, get_exchange_rates, create_notification, notify_admins, compress_image
from sponsor.models import SponsorProfile, PaymentReceipt, PaymentSchedule
from sponsor.views.base import sponsor_required, _get_profile


@sponsor_required
def compare_view(request):
    notif_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    return render(request, 'sponsor/compare.html', {
        'notif_count': notif_count,
    })


@sponsor_required
@require_GET
def compare_list(request):
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from django.db.models import Q

    q         = request.GET.get('q', '').strip()
    user_type = request.GET.get('type', '')
    profile   = _get_profile(request.user)

    # المستفيدون المكفولون من هذا الكافل + الغير مكفولين
    # نجمع IDs من الاستمارات
    sponsored_ids = set()
    sponsored_ids.update(OrphanForm.objects.filter(sponsor=profile).values_list('user_id', flat=True))
    sponsored_ids.update(SpecialNeedsForm.objects.filter(sponsor=profile).values_list('user_id', flat=True))
    sponsored_ids.update(FamilyForm.objects.filter(sponsor=profile).values_list('user_id', flat=True))

    free_ids = set()
    free_ids.update(OrphanForm.objects.filter(sponsor__isnull=True, user__is_approved=True).values_list('user_id', flat=True))
    free_ids.update(SpecialNeedsForm.objects.filter(sponsor__isnull=True, user__is_approved=True).values_list('user_id', flat=True))
    free_ids.update(FamilyForm.objects.filter(sponsor__isnull=True, user__is_approved=True).values_list('user_id', flat=True))

    allowed_ids = sponsored_ids | free_ids

    qs = CustomUser.objects.filter(
        pk__in=allowed_ids,
        is_approved=True,
    ).exclude(user_type__in=['admin', 'sponsor'])

    if user_type:
        qs = qs.filter(user_type=user_type)

    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)  |
            Q(family_name__icontains=q) |
            Q(id_number__icontains=q)   |
            Q(registration_number__icontains=q)
        )

    users = qs.order_by('first_name')[:50]

    TYPE_LABELS = {'orphan':'يتيم', 'family':'أسرة', 'special':'ذوو احتياجات'}

    return JsonResponse({'users': [{
        'id':         str(u.pk),
        'full_name':  u.get_full_name(),
        'reg_number': u.registration_number or '—',
        'id_number':  u.id_number or '—',
        'user_type':  u.user_type,
        'type_label': TYPE_LABELS.get(u.user_type, u.user_type),
        'is_mine':    u.pk in sponsored_ids,
    } for u in users]})

@sponsor_required
@require_GET
def compare_data(request):
    """جلب بيانات المستفيدين للمقارنة"""
    ids = request.GET.get('ids', '').split(',')
    ids = [i.strip() for i in ids if i.strip()][:4]

    if not ids:
        return JsonResponse({'error': 'لا يوجد مستفيدون'}, status=400)

    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm
    from django.utils import timezone

    TYPE_LABELS = {'orphan': 'يتيم', 'family': 'أسرة', 'special': 'ذوو احتياجات'}
    MODEL_MAP   = {'orphan': OrphanForm, 'family': FamilyForm, 'special': SpecialNeedsForm}
    AID_TYPES   = {
        'food':'غذائية','medical':'طبية','financial':'مالية',
        'clothing':'ملابس','furniture':'أثاث','education':'تعليمية','other':'أخرى',
    }
    STATUS_MAP  = {'paid':'مدفوعة','pending':'معلّقة','late':'متأخرة'}

    results = []
    today   = timezone.now()

    for uid in ids:
        try:
            user = CustomUser.objects.get(pk=uid)
        except CustomUser.DoesNotExist:
            continue

        # الكافل
        sponsor_name = None
        status       = None
        health       = None
        education    = None
        housing      = None
        city         = None
        story        = None
        photo        = None

        Model = MODEL_MAP.get(user.user_type)
        if Model:
            try:
                form = Model.objects.get(user=user)
                status    = form.status
                if hasattr(form, 'photo') and form.photo:
                    photo = form.photo.url
                if hasattr(form, 'sponsor') and form.sponsor:
                    sponsor_name = form.sponsor.user.get_full_name()
                if hasattr(form, 'health_status'):
                    health = form.health_status
                if hasattr(form, 'education_level'):
                    education = form.education_level
                if hasattr(form, 'housing_type'):
                    housing = form.housing_type
                if hasattr(form, 'current_city'):
                    city = form.current_city
                if hasattr(form, 'story'):
                    story = form.story
            except Model.DoesNotExist:
                pass

        # المدفوعات
        pays          = Payment.objects.filter(beneficiary=user)
        total_pays    = pays.aggregate(s=Sum('amount_ils'))['s'] or 0
        month_pays    = pays.filter(
            date__year=today.year, date__month=today.month
        ).aggregate(s=Sum('amount_ils'))['s'] or 0
        late_pays     = pays.filter(status='late').count()
        pays_count    = pays.count()

        # المساعدات
        aids_qs       = Aid.objects.filter(beneficiary=user)
        total_aids    = aids_qs.count()
        aids_by_type  = {}
        for aid in aids_qs:
            label = AID_TYPES.get(aid.aid_type, aid.aid_type)
            aids_by_type[label] = aids_by_type.get(label, 0) + 1

        # آخر دفعة
        last_pay = pays.order_by('-date').first()

        results.append({
            'id':           str(user.pk),
            'full_name':    user.get_full_name(),
            'reg_number':   user.registration_number or '—',
            'id_number':    user.id_number or '—',
            'user_type':    user.user_type,
            'type_label':   TYPE_LABELS.get(user.user_type, ''),
            'gender':       user.gender or '—',
            'nationality':  user.nationality or '—',
            'date_joined':  user.date_joined.strftime('%Y/%m/%d'),
            'last_login':   user.last_login.strftime('%Y/%m/%d') if user.last_login else '—',
            'is_active':    user.is_active,
            'is_approved':  user.is_approved,
            'allow_comm':   getattr(user, 'allow_direct_comm', False),
            'photo':        photo,
            'sponsor_name': sponsor_name or 'غير مكفول',
            'status':       status or '—',
            'health':       health or '—',
            'education':    education or '—',
            'housing':      housing or '—',
            'city':         city or '—',
            'story':        story or '',
            'total_pays':   str(round(total_pays, 2)),
            'month_pays':   str(round(month_pays, 2)),
            'pays_count':   pays_count,
            'late_pays':    late_pays,
            'last_pay':     str(last_pay.date) if last_pay else '—',
            'total_aids':   total_aids,
            'aids_by_type': aids_by_type,
        })

    return JsonResponse({'users': results})
