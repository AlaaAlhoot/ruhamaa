"""
beneficiary/views/dashboard.py
الصفحة الرئيسية للمستفيد - شاملة ومحسّنة
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Max
from django.utils import timezone

from core.models import Payment, Aid, Notification
from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm

ALLOWED_BENE_TYPES = ('orphan', 'special', 'family')

ARABIC_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

# مراحل الطلب
STATUS_FLOW = [
    ('مسودة',          'تم تسجيلك لكن لم يكتمل ملفك بعد'),
    ('مرسلة',          'تم إرسال الطلب وينتظر المراجعة'),
    ('قيد المراجعة',   'الإدارة تراجع طلبك حالياً'),
    ('مقبولة',         'تمت الموافقة على طلبك'),
    ('قيد التدقيق',    'يتم التحقق من بياناتك ومستنداتك'),
    ('قيد التكفل',     'البحث عن كافل لك'),
    ('متكفّل',         'تم تخصيص كافل لك ✨'),
]


# ════════════════════════════════════════════
#  Helpers
# ════════════════════════════════════════════

def _bene_required(request):
    return request.user.is_authenticated and request.user.user_type in ALLOWED_BENE_TYPES


def _get_form(user):
    """جلب استمارة المستفيد."""
    Model = {
        'orphan':  OrphanForm,
        'special': SpecialNeedsForm,
        'family':  FamilyForm,
    }.get(user.user_type)
    if not Model:
        return None
    try:
        return Model.objects.select_related('sponsor__user').get(user=user)
    except Model.DoesNotExist:
        return None


def _get_status_steps(current_status):
    """بناء خطوات شريط التقدم."""
    current_status = (current_status or 'مسودة').strip()
    steps = []
    found_active = False

    for label, desc in STATUS_FLOW:
        is_done = is_active = False

        if not found_active:
            if label == current_status or (
                'متكفّل' in current_status and label == 'متكفّل'
            ) or (
                'تكفل' in current_status and 'تكفل' in label
            ) or (
                'تدقيق' in current_status and 'تدقيق' in label
            ) or (
                'مراجعة' in current_status and 'مراجعة' in label
            ):
                is_active = True
                found_active = True
            else:
                is_done = True

        steps.append({
            'label':       label,
            'description': desc,
            'done':        is_done,
            'active':      is_active,
        })

    # لو لم يتم العثور على match، نعتبر أول خطوة active
    if not any(s['active'] for s in steps) and steps:
        for s in steps:
            s['done'] = False
        steps[0]['active'] = True

    return steps


def _get_greeting():
    """تحية حسب الوقت."""
    hour = timezone.now().hour
    if 5 <= hour < 12:
        return 'صباح الخير', '☀️'
    elif 12 <= hour < 17:
        return 'مساء النور', '🌤️'
    elif 17 <= hour < 21:
        return 'مساء الخير', '🌆'
    else:
        return 'مساء الخير', '🌙'


def _format_arabic_date(d):
    if not d:
        return ''
    return f'{d.day} {ARABIC_MONTHS[d.month - 1]} {d.year}'


def _days_ago(d):
    """كم يوم مضى من تاريخ معين."""
    if not d:
        return None
    return (timezone.now().date() - d).days


def _build_smart_alerts(user, form, last_payment, unread_notif_count):
    """تنبيهات ذكية تظهر للمستفيد."""
    alerts = []

    # تنبيه عدم اكتمال الملف
    status = (form.status if form else 'مسودة')
    if status == 'مسودة':
        alerts.append({
            'icon': '⚠️',
            'type': 'warning',
            'text': 'ملفك غير مكتمل بعد. أكمل بياناتك ليتم مراجعة طلبك.',
            'action_url': '/beneficiary/profile/',
            'action_label': 'إكمال الملف',
        })

    # تنبيه إشعارات جديدة
    if unread_notif_count > 0:
        alerts.append({
            'icon': '🔔',
            'type': 'info',
            'text': f'لديك {unread_notif_count} إشعار جديد',
            'action_url': '#notifications',
            'action_label': 'عرض',
        })

    # تنبيه آخر دفعة
    if last_payment:
        days = _days_ago(last_payment.date)
        if days is not None:
            if days <= 7:
                alerts.append({
                    'icon': '✅',
                    'type': 'success',
                    'text': f'استلمت آخر دفعة منذ {days} يوم — {last_payment.amount_ils:.0f} ₪',
                    'action_url': '/beneficiary/payments/',
                    'action_label': 'التفاصيل',
                })

    # تنبيه إذا لا يوجد كافل
    if form and not form.sponsor and status not in ('مسودة', 'مرسلة'):
        alerts.append({
            'icon': '💚',
            'type': 'info',
            'text': 'نحن نبحث لك عن كافل مناسب — سيتم إعلامك فور تخصيصه',
            'action_url': None,
            'action_label': None,
        })

    return alerts


def _build_sponsor_info(form, user):
    """بيانات الكافل."""
    if not form or not form.sponsor:
        return None

    sp = form.sponsor
    sp_user = sp.user
    start_date = form.sponsorship_date

    # مدة الكفالة
    duration_str = ''
    if start_date:
        days = (timezone.now().date() - start_date).days
        years = days // 365
        months = (days % 365) // 30
        if years > 0 and months > 0:
            duration_str = f'{years} سنة و {months} شهر'
        elif years > 0:
            duration_str = f'{years} سنة'
        elif months > 0:
            duration_str = f'{months} شهر'
        else:
            duration_str = f'{days} يوم'

    return {
        'full_name':  sp_user.get_full_name(),
        'photo':      sp.photo.url if sp.photo else None,
        'country':    sp.country or '',
        'city':       sp.city or '',
        'job':        sp.job or '',
        'start_date': _format_arabic_date(start_date),
        'duration':   duration_str,
    }


def _build_mini_chart(user):
    """بيانات mini chart لآخر 6 أشهر."""
    today = timezone.now().date()
    labels = []
    values = []

    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        total = Payment.objects.filter(
            beneficiary=user, date__year=y, date__month=m
        ).aggregate(s=Sum('amount_ils'))['s'] or Decimal('0')
        labels.append(f'{ARABIC_MONTHS[m-1][:3]}')
        values.append(float(total))

    return {'labels': labels, 'values': values}


def _build_timeline(user, limit=10):
    """جدول زمني موحّد للأحداث الأخيرة."""
    events = []

    # المدفوعات
    for p in Payment.objects.filter(beneficiary=user).order_by('-date')[:5]:
        events.append({
            'icon':   '💰',
            'title':  f'دفعة {dict(Payment.PAID_BY).get(p.paid_by, "")}',
            'date':   _format_arabic_date(p.date),
            'amount': f'{p.amount_ils:.0f} ₪',
            'tag':    dict(Payment.STATUS).get(p.status, p.status),
            '_dt':    timezone.make_aware(datetime.combine(p.date, datetime.min.time())) if p.date else timezone.make_aware(datetime.min),
        })

    # المساعدات
    for a in Aid.objects.filter(beneficiary=user).order_by('-date')[:5]:
        events.append({
            'icon':   '🎁',
            'title':  a.name,
            'date':   _format_arabic_date(a.date),
            'amount': '',
            'tag':    dict(Aid.AID_TYPES).get(a.aid_type, ''),
            '_dt':    timezone.make_aware(datetime.combine(a.date, datetime.min.time())) if a.date else timezone.make_aware(datetime.min),
        })

    # الإشعارات
    for n in Notification.objects.filter(recipient=user).order_by('-created_at')[:3]:
        events.append({
            'icon':   '🔔',
            'title':  n.title or 'إشعار',
            'date':   _format_arabic_date(n.created_at.date()) if n.created_at else '',
            'amount': '',
            'tag':    '',
            '_dt':    n.created_at if n.created_at else timezone.make_aware(datetime.min),
        })

    events.sort(key=lambda e: e['_dt'], reverse=True)
    for e in events:
        e.pop('_dt', None)
    return events[:limit]


# ════════════════════════════════════════════
#  Page View
# ════════════════════════════════════════════

@login_required(login_url='/login/')
def dashboard_view(request):
    if not _bene_required(request):
        return redirect('/')
    return render(request, 'beneficiary/dashboard.html', {})


# ════════════════════════════════════════════
#  Data API
# ════════════════════════════════════════════

@login_required(login_url='/login/')
@require_GET
def dashboard_data_api(request):
    if not _bene_required(request):
        return JsonResponse({'status': 'error', 'message': 'غير مسموح'}, status=403)

    user = request.user
    form = _get_form(user)

    # ─── تحية ─── 
    greeting, greeting_icon = _get_greeting()

    # ─── الإحصائيات ─── 
    payments_qs = Payment.objects.filter(beneficiary=user)
    aids_qs = Aid.objects.filter(beneficiary=user)

    total_ils = payments_qs.aggregate(s=Sum('amount_ils'))['s'] or Decimal('0')
    total_usd = payments_qs.aggregate(s=Sum('amount_usd'))['s'] or Decimal('0')
    payments_count = payments_qs.count()
    aids_count = aids_qs.count()

    # آخر دفعة
    last_payment = payments_qs.order_by('-date').first()
    last_payment_data = None
    if last_payment:
        last_payment_data = {
            'date':     _format_arabic_date(last_payment.date),
            'amount':   str(last_payment.amount_ils),
            'days_ago': _days_ago(last_payment.date),
        }

    # ─── الكافل ─── 
    sponsor = _build_sponsor_info(form, user)

    # مدة الكفالة بالأشهر
    sponsorship_months = None
    if form and form.sponsorship_date:
        days = (timezone.now().date() - form.sponsorship_date).days
        sponsorship_months = days // 30

    # ─── شريط التقدم ─── 
    status = form.status if form else 'مسودة'
    status_steps = _get_status_steps(status)
    current_step_desc = next((s['description'] for s in status_steps if s['active']),
                              'لم يبدأ طلبك بعد')

    # ─── الإشعارات ─── 
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count()
    notifications_list = []
    for n in Notification.objects.filter(recipient=user).order_by('-created_at')[:5]:
        time_ago = ''
        if n.created_at:
            seconds = (timezone.now() - n.created_at).total_seconds()
            if seconds < 60: time_ago = 'الآن'
            elif seconds < 3600: time_ago = f'منذ {int(seconds//60)} دقيقة'
            elif seconds < 86400: time_ago = f'منذ {int(seconds//3600)} ساعة'
            else: time_ago = f'منذ {int(seconds//86400)} يوم'

        notifications_list.append({
            'id':       n.pk,
            'title':    n.title or '—',
            'message':  (n.message or '')[:80],
            'ntype':    n.ntype or 'INFO',
            'is_read':  n.is_read,
            'time_ago': time_ago,
        })

    # ─── التنبيهات الذكية ─── 
    alerts = _build_smart_alerts(user, form, last_payment, unread_count)

    # ─── Timeline ─── 
    timeline = _build_timeline(user, limit=10)

    # ─── Mini Chart ─── 
    mini_chart = _build_mini_chart(user)

    # ─── الصورة ─── 
    user_photo = None
    if form and form.photo:
        user_photo = form.photo.url

    return JsonResponse({
        'status': 'success',
        'data': {
            'user': {
                'first_name':  user.first_name,
                'full_name':   user.get_full_name(),
                'photo':       user_photo,
                'reg_number':  user.registration_number or '',
                'id_number':   user.id_number or '',
                'form_number': form.form_number if form else '',
            },
            'greeting':       greeting,
            'greeting_icon':  greeting_icon,
            'status':         status,
            'status_steps':   status_steps,
            'current_step_desc': current_step_desc,
            'summary': {
                'total_ils':           str(total_ils),
                'total_usd':           str(total_usd),
                'payments_count':      payments_count,
                'aids_count':          aids_count,
                'last_payment':        last_payment_data,
                'sponsorship_months':  sponsorship_months,
            },
            'sponsor':        sponsor,
            'alerts':         alerts,
            'unread_count':   unread_count,
            'notifications':  notifications_list,
            'timeline':       timeline,
            'mini_chart':     mini_chart,
        }
    })


# ════════════════════════════════════════════
#  Mark Notifications Read
# ════════════════════════════════════════════

@login_required(login_url='/login/')
@require_POST
@csrf_protect
def mark_notifications_read_api(request):
    if not _bene_required(request):
        return JsonResponse({'status': 'error', 'message': 'غير مسموح'}, status=403)

    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success', 'message': 'تم تحديد الكل كمقروء'})
