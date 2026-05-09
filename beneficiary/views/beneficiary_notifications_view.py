"""
beneficiary/views/notifications_view.py
صفحة الإشعارات — لوحة المستفيد
"""
from functools import wraps
from datetime import timedelta

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.utils import timezone

from core.models import Notification
from core.utils import fmt_dt

# ══ ثوابت ══
NTYPE_ICONS = {
    'NEW_MSG':      '💬',
    'RECEIPT_OK':   '✅',
    'RECEIPT_REJ':  '❌',
    'PAYMENT_DUE':  '📅',
    'END_SPONSOR':  '💔',
    'NEW_RECEIPT':  '📩',
    'INFO_REQUEST': '📋',
    'SYSTEM':       '🔔',
}
NTYPE_LABELS = {
    'NEW_MSG':      'رسالة جديدة',
    'RECEIPT_OK':   'وصل مقبول',
    'RECEIPT_REJ':  'وصل مرفوض',
    'PAYMENT_DUE':  'تذكير دفعة',
    'END_SPONSOR':  'إنهاء كفالة',
    'NEW_RECEIPT':  'وصل جديد',
    'INFO_REQUEST': 'طلب معلومات',
    'SYSTEM':       'إشعار نظام',
}

# ══ Decorator ══
def beneficiary_required(view_func):
    """يتحقق أن المستخدم مستفيد موافق عليه"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if request.user.user_type not in ['orphan', 'family', 'special']:
            return redirect('/login/')
        if not request.user.is_approved:
            return render(request, 'beneficiary/pending.html')
        return view_func(request, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════

@beneficiary_required
def notifications(request):
    user        = request.user
    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()
    return render(request, 'beneficiary/notifications.html', {
        'notif_count': notif_count,
    })


# ══════════════════════════════════════════════════════════
# AJAX — جلب الإشعارات
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_GET
def notifications_data(request):
    user      = request.user
    status    = request.GET.get('status', 'unread')  # unread | read | all
    ntype     = request.GET.get('ntype',  '')
    period    = request.GET.get('period', 'all')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to',   '')

    qs = Notification.objects.filter(recipient=user).select_related('sender')

    # فلتر الحالة
    if status == 'unread':
        qs = qs.filter(is_read=False)
    elif status == 'read':
        qs = qs.filter(is_read=True)

    # فلتر النوع
    if ntype:
        qs = qs.filter(ntype=ntype)

    # فلتر التاريخ
    now = timezone.now()
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - timedelta(days=30))
    elif period == 'custom' and date_from and date_to:
        import datetime
        d_from = timezone.make_aware(datetime.datetime.combine(
            datetime.date.fromisoformat(date_from), datetime.time.min))
        d_to   = timezone.make_aware(datetime.datetime.combine(
            datetime.date.fromisoformat(date_to),   datetime.time.max))
        qs = qs.filter(created_at__gte=d_from, created_at__lte=d_to)

    qs = qs.order_by('-created_at')

    # أنواع الإشعارات
    NTYPE_ICONS = {
        'NEW_MSG':      '💬',
        'RECEIPT_OK':   '✅',
        'RECEIPT_REJ':  '❌',
        'PAYMENT_DUE':  '📅',
        'END_SPONSOR':  '💔',
        'NEW_RECEIPT':  '📩',
        'INFO_REQUEST': '📋',
        'SYSTEM':       '🔔',
    }
    NTYPE_LABELS = {
        'NEW_MSG':      'رسالة جديدة',
        'RECEIPT_OK':   'وصل مقبول',
        'RECEIPT_REJ':  'وصل مرفوض',
        'PAYMENT_DUE':  'تذكير دفعة',
        'END_SPONSOR':  'إنهاء كفالة',
        'NEW_RECEIPT':  'وصل جديد',
        'INFO_REQUEST': 'طلب معلومات',
        'SYSTEM':       'إشعار نظام',
    }

    def _fmt(n):
        return {
            'id':          n.pk,
            'ntype':       n.ntype,
            'icon':        NTYPE_ICONS.get(n.ntype, '🔔'),
            'type_label':  NTYPE_LABELS.get(n.ntype, n.ntype),
            'title':       n.title,
            'message':     n.message,
            'is_read':     n.is_read,
            'action_url':  n.action_url or '',
            'created_at':  fmt_dt(n.created_at),
            'sender':      n.sender.get_full_name() if n.sender else 'النظام',
        }

    items = [_fmt(n) for n in qs]

    # إحصائيات
    all_qs    = Notification.objects.filter(recipient=user)
    unread_qs = all_qs.filter(is_read=False)

    stats = {
        'total':  all_qs.count(),
        'unread': unread_qs.count(),
        'read':   all_qs.filter(is_read=True).count(),
        'today':  all_qs.filter(created_at__date=now.date()).count(),
    }

    # أنواع الإشعارات المتاحة للفلترة
    available_types = list(all_qs.values_list('ntype', flat=True).distinct())
    types_list = [
        {'ntype': t, 'label': NTYPE_LABELS.get(t, t), 'icon': NTYPE_ICONS.get(t, '🔔')}
        for t in available_types
    ]

    return JsonResponse({
        'items': items,
        'stats': stats,
        'types': types_list,
    })


# ══════════════════════════════════════════════════════════
# قراءة إشعار واحد
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_POST
@csrf_protect
def mark_read(request):
    user = request.user
    nid  = request.POST.get('id', '').strip()

    try:
        n = Notification.objects.get(pk=nid, recipient=user)
        n.is_read = True
        n.save(update_fields=['is_read'])
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الإشعار غير موجود'})


# ══════════════════════════════════════════════════════════
# قراءة كل الإشعارات
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_POST
@csrf_protect
def mark_all_read(request):
    user  = request.user
    count = Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
    return JsonResponse({
        'status':  'success',
        'message': f'تم تحديد {count} إشعار كمقروء',
        'count':   count,
    })


# ══════════════════════════════════════════════════════════
# حذف إشعار
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_POST
@csrf_protect
def delete_notification(request):
    user = request.user
    nid  = request.POST.get('id', '').strip()

    try:
        n = Notification.objects.get(pk=nid, recipient=user)
        n.delete()
        return JsonResponse({'status': 'success', 'message': 'تم حذف الإشعار'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الإشعار غير موجود'})


# ══════════════════════════════════════════════════════════
# حذف كل الإشعارات المقروءة
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_POST
@csrf_protect
def delete_all_read(request):
    user  = request.user
    count = Notification.objects.filter(recipient=user, is_read=True).delete()[0]
    return JsonResponse({
        'status':  'success',
        'message': f'تم حذف {count} إشعار مقروء',
        'count':   count,
    })


# ══════════════════════════════════════════════════════════
# معاينة الإشعارات (Dropdown)
# ══════════════════════════════════════════════════════════

@beneficiary_required
@require_GET
def notifications_preview(request):
    user   = request.user
    notifs = Notification.objects.filter(recipient=user).order_by('-created_at')[:3]
    return JsonResponse({
        'unread_count': Notification.objects.filter(recipient=user, is_read=False).count(),
        'notifications': [
            {
                'message': n.title or n.message,
                'time':    fmt_dt(n.created_at),
                'icon':    NTYPE_ICONS.get(n.ntype, '🔔'),
                'url':     n.action_url or '',
                'is_read': n.is_read,
            }
            for n in notifs
        ],
    })
