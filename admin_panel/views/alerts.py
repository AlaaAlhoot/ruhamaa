"""
admin_panel/views/alerts.py
نظام التنبيهات الذكية
"""

from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q, Count, Sum

from core.models import CustomUser, SmartAlert, Payment, Aid, Notification
from core.utils import fmt_dt
from .decorators import admin_required


# ══════════════════════════════════════════════
#  مساعدات
# ══════════════════════════════════════════════

def _exists(alert_type, target_user=None):
    """هل يوجد تنبيه نشط من نفس النوع لنفس المستخدم؟"""
    qs = SmartAlert.objects.filter(alert_type=alert_type, status='active')
    if target_user:
        qs = qs.filter(target_user=target_user)
    else:
        qs = qs.filter(target_user__isnull=True)
    return qs.exists()


def _create(alert_type, level, title, message,
            target_user=None, action_url=None, extra_data=None):
    """إنشاء أو تحديث تنبيه"""
    qs = SmartAlert.objects.filter(alert_type=alert_type, status='active')
    if target_user:
        qs = qs.filter(target_user=target_user)
    else:
        qs = qs.filter(target_user__isnull=True)

    existing = qs.first()
    if existing:
        existing.message    = message
        existing.title      = title
        existing.extra_data = extra_data or {}
        existing.save(update_fields=['message', 'title', 'extra_data'])
        return existing

    return SmartAlert.objects.create(
        alert_type  = alert_type,
        level       = level,
        title       = title,
        message     = message,
        target_user = target_user,
        action_url  = action_url or '',
        extra_data  = extra_data or {},
    )

def _date_filter(qs, period, date_from=None, date_to=None, field='created_at'):
    """تطبيق فلتر التاريخ"""
    now = timezone.now()
    if period == 'today':
        qs = qs.filter(**{f'{field}__date': now.date()})
    elif period == 'week':
        qs = qs.filter(**{f'{field}__gte': now - timedelta(days=7)})
    elif period == 'month':
        qs = qs.filter(**{f'{field}__gte': now - timedelta(days=30)})
    elif period == 'six_months':
        qs = qs.filter(**{f'{field}__gte': now - timedelta(days=180)})
    elif period == 'year':
        qs = qs.filter(**{f'{field}__gte': now - timedelta(days=365)})
    elif period == 'custom' and date_from and date_to:
        import datetime
        d_from = timezone.make_aware(datetime.datetime.combine(
            datetime.date.fromisoformat(date_from), datetime.time.min))
        d_to   = timezone.make_aware(datetime.datetime.combine(
            datetime.date.fromisoformat(date_to),   datetime.time.max))
        qs = qs.filter(**{f'{field}__gte': d_from, f'{field}__lte': d_to})
    # 'all' → لا فلتر
    return qs


# ══════════════════════════════════════════════
#  محرك التنبيهات
# ══════════════════════════════════════════════

def run_smart_alerts():
    """فحص جميع الشروط وإنشاء التنبيهات المناسبة"""
    from datetime import timedelta
    import calendar

    now   = timezone.now()
    today = now.date()

    from beneficiary import OrphanForm, FamilyForm, SpecialNeedsForm
    from sponsor.models import SponsorProfile
    from core.models import ActivityLog

    bene_qs = CustomUser.objects.filter(
        is_approved=True
    ).exclude(user_type__in=['admin', 'sponsor'])

    # ── 🔴 حرجة ──────────────────────────────

    # 1. NO_PAYMENT_30D — مستفيد بدون دفعة 30+ يوم
    for user in bene_qs.filter(is_active=True):
        last_pay = Payment.objects.filter(beneficiary=user).order_by('-date').first()
        if last_pay:
            days = (today - last_pay.date).days
        else:
            days = (today - user.date_joined.date()).days

        if days >= 30:
            _create(
                'NO_PAYMENT_30D', 'critical',
                f'بدون دفعة — {user.get_full_name()}',
                f'لم تُسجَّل أي دفعة منذ {days} يوم' if last_pay
                else f'لم تُسجَّل أي دفعة قط — انضم منذ {days} يوم',
                target_user  = user,
                action_url   = f'/admin-panel/orphans/?open={user.pk}',
                extra_data   = {'days': days},
            )
        else:
            _resolve('NO_PAYMENT_30D', target_user=user)

    # 2. NO_SPONSOR_30D — مستفيد معتمد بدون كافل 30+ يوم
    for user in bene_qs.filter(is_active=True):
        MODEL = {
            'orphan':  OrphanForm,
            'family':  FamilyForm,
            'special': SpecialNeedsForm,
        }.get(user.user_type)
        if not MODEL:
            continue
        try:
            form = MODEL.objects.get(user=user)
            if hasattr(form, 'sponsor') and form.sponsor:
                _resolve('NO_SPONSOR_30D', target_user=user)
                continue
        except MODEL.DoesNotExist:
            continue
        days = (today - user.date_joined.date()).days
        if days >= 30:
            _create(
                'NO_SPONSOR_30D', 'critical',
                f'بدون كافل — {user.get_full_name()}',
                f'مستفيد معتمد منذ {days} يوم ولا يوجد كافل',
                target_user = user,
                action_url  = f'/admin-panel/orphans/?open={user.pk}',
                extra_data  = {'days': days},
            )
        else:
            _resolve('NO_SPONSOR_30D', target_user=user)

    # 3. LATE_PAYMENT_7D — دفعات متأخرة 7+ أيام
    late_pays = Payment.objects.filter(
        status = 'late',
        date__lte = today - timedelta(days=7),
    ).select_related('beneficiary')
    for pay in late_pays:
        days = (today - pay.date).days
        _create(
            'LATE_PAYMENT_7D', 'critical',
            f'دفعة متأخرة — {pay.beneficiary.get_full_name()}',
            f'دفعة بقيمة {pay.amount_ils}₪ متأخرة منذ {days} يوم',
            target_user = pay.beneficiary,
            action_url  = f'/admin-panel/orphans/?open={pay.beneficiary.pk}',
            extra_data  = {'pay_id': pay.pk, 'amount': str(pay.amount_ils), 'days': days},
        )

    # 4. DISABLED_SPONSORED — معطّل ومكفول
    for user in bene_qs.filter(is_active=False):
        MODEL = {
            'orphan':  OrphanForm,
            'family':  FamilyForm,
            'special': SpecialNeedsForm,
        }.get(user.user_type)
        if not MODEL:
            continue
        try:
            form = MODEL.objects.get(user=user)
            if hasattr(form, 'sponsor') and form.sponsor:
                _create(
                    'DISABLED_SPONSORED', 'critical',
                    f'حساب معطّل ومكفول — {user.get_full_name()}',
                    f'الحساب معطّل بينما لا يزال مكفولاً من {form.sponsor.user.get_full_name()}',
                    target_user = user,
                )
            else:
                _resolve('DISABLED_SPONSORED', target_user=user)
        except MODEL.DoesNotExist:
            pass

    # 5. SPONSOR_NO_PAY_2M — كافل لم يدفع شهرين
    two_months_ago = today - timedelta(days=60)
    for sp_user in CustomUser.objects.filter(user_type='sponsor', is_active=True):
        last = Payment.objects.filter(sponsor=sp_user).order_by('-date').first()
        if last:
            days = (today - last.date).days
        else:
            days = (today - sp_user.date_joined.date()).days

        if last is None or last.date <= two_months_ago:
            _create(
                'SPONSOR_NO_PAY_2M', 'critical',
                f'كافل لم يدفع — {sp_user.get_full_name()}',
                f'لم يتم تسجيل أي دفعة منذ {days} يوم' if last
                else f'لم يسجّل أي دفعة قط — انضم منذ {days} يوم',
                target_user = sp_user,
                extra_data  = {'days': days},
            )
        else:
            _resolve('SPONSOR_NO_PAY_2M', target_user=sp_user)

    # 6. SPONSOR_REMOVED_14D — فقد الكافل 14+ يوم
    recent_removals = ActivityLog.objects.filter(
        action       = 'UPDATE',
        description__icontains = 'إزالة كافل',
        created_at__gte        = now - timedelta(days=14),
    )
    for log in recent_removals:
        if log.target_id:
            try:
                user = CustomUser.objects.get(pk=log.target_id)
                days = (today - log.created_at.date()).days
                _create(
                    'SPONSOR_REMOVED_14D', 'critical',
                    f'فقد الكافل — {user.get_full_name()}',
                    f'تم إزالة الكافل منذ {days} يوم ولم يُعيَّن بديل',
                    target_user = user,
                    extra_data  = {'days': days},
                )
            except (CustomUser.DoesNotExist, Exception):
                pass

    # ── 🟠 عالية ──────────────────────────────

    # 7. PENDING_REQ_7D — طلبات معلّقة 7+ أيام
    pending_count = CustomUser.objects.filter(
        is_approved = False,
        is_active   = True,
        date_joined__lte = now - timedelta(days=7),
    ).exclude(user_type='admin').count()
    if pending_count > 0:
        _create(
            'PENDING_REQ_7D', 'high',
            f'طلبات معلّقة ({pending_count})',
            f'يوجد {pending_count} طلب تسجيل معلّق منذ أكثر من 7 أيام دون مراجعة',
            action_url = '/admin-panel/requests/',
            extra_data = {'count': pending_count},
        )
    else:
        _resolve('PENDING_REQ_7D')

    # 8. NO_LOGIN_60D — لم يسجل دخولاً 60+ يوم
    sixty_days_ago = now - timedelta(days=60)
    for user in CustomUser.objects.filter(
        is_active   = True,
        is_approved = True,
    ).exclude(user_type='admin').filter(
        Q(last_login__isnull=True) | Q(last_login__lte=sixty_days_ago)
    ):
        if user.last_login:
            days = (now - user.last_login).days
        else:
            days = (now - user.date_joined).days

        _create(
            'NO_LOGIN_60D', 'high',
            f'لم يسجل دخولاً — {user.get_full_name()}',
            f'لم يسجل دخولاً منذ {days} يوم' if user.last_login
            else f'لم يسجل دخولاً قط — انضم منذ {days} يوم',
            target_user = user,
            extra_data  = {'days': days},
        )

    # 9. SPECIAL_NO_AID_60D — ذوو احتياجات بدون مساعدة طبية 60+ يوم
    for user in bene_qs.filter(user_type='special', is_active=True):
        last_aid = Aid.objects.filter(
            beneficiary = user,
            aid_type    = 'medical',
        ).order_by('-date').first()
        if last_aid:
            days = (today - last_aid.date).days
        else:
            days = (today - user.date_joined.date()).days

        if days >= 60:
            _create(
                'SPECIAL_NO_AID_60D', 'high',
                f'بدون مساعدة طبية — {user.get_full_name()}',
                f'لم يتلقَّ أي مساعدة طبية منذ {days} يوم' if last_aid
                else f'لم يتلقَّ أي مساعدة طبية قط — انضم منذ {days} يوم',
                target_user = user,
                extra_data  = {'days': days},
            )
        else:
            _resolve('SPECIAL_NO_AID_60D', target_user=user)

    # 10. HIGH_UNSPONSORED — غير مكفولين تجاوز 20%
    total_bene      = bene_qs.count()
    sponsored_count = 0
    for Model in [OrphanForm, FamilyForm, SpecialNeedsForm]:
        sponsored_count += Model.objects.filter(sponsor__isnull=False).count()
    unsponsored = total_bene - sponsored_count
    if total_bene > 0 and (unsponsored / total_bene) >= 0.2:
        pct = round((unsponsored / total_bene) * 100)
        _create(
            'HIGH_UNSPONSORED', 'high',
            f'نسبة غير المكفولين مرتفعة ({pct}%)',
            f'{unsponsored} مستفيد من أصل {total_bene} بدون كافل — النسبة {pct}%',
            action_url = '/admin-panel/orphans/',
            extra_data = {'pct': pct, 'count': unsponsored},
        )
    else:
        _resolve('HIGH_UNSPONSORED')

    # 11. SPONSOR_3_LATE — كافل 3+ دفعات متأخرة
    for sp_user in CustomUser.objects.filter(user_type='sponsor', is_active=True):
        late = Payment.objects.filter(sponsor=sp_user, status='late').count()
        if late >= 3:
            _create(
                'SPONSOR_3_LATE', 'high',
                f'كافل لديه {late} دفعات متأخرة — {sp_user.get_full_name()}',
                f'تراكمت {late} دفعات متأخرة على الكافل {sp_user.get_full_name()}',
                target_user = sp_user,
                extra_data  = {'count': late},
            )
        else:
            _resolve('SPONSOR_3_LATE', target_user=sp_user)

    # 12. PROFILE_OUTDATED_6M — ملف لم يُحدَّث 6 أشهر
    six_months_ago = now - timedelta(days=180)
    for user in bene_qs.filter(is_active=True, date_joined__lte=six_months_ago):
        last_log = ActivityLog.objects.filter(
            Q(target_id=str(user.pk), target_model='CustomUser') |
            Q(description__icontains=user.get_full_name())
        ).order_by('-created_at').first()
        if not last_log or last_log.created_at <= six_months_ago:
            days = (now - last_log.created_at).days if last_log else (now - user.date_joined).days
            _create(
                'PROFILE_OUTDATED_6M', 'high',
                f'ملف قديم — {user.get_full_name()}',
                f'لم يُحدَّث ملف هذا المستفيد منذ {days} يوم',
                target_user = user,
                extra_data  = {'days': days},
            )
        else:
            _resolve('PROFILE_OUTDATED_6M', target_user=user)

    # ── 🟡 متوسطة ──────────────────────────────

    # 13. NO_AIDS_THIS_MONTH — لا مساعدات هذا الشهر
    aids_this_month = Aid.objects.filter(
        date__year  = today.year,
        date__month = today.month,
    ).count()
    if aids_this_month == 0:
        _create(
            'NO_AIDS_THIS_MONTH', 'medium',
            'لا توجد مساعدات هذا الشهر',
            f'لم يتم تسجيل أي مساعدة في شهر {today.month}/{today.year}',
            action_url = '/admin-panel/orphans/',
        )
    else:
        _resolve('NO_AIDS_THIS_MONTH')

    # 14. NO_PAYS_THIS_MONTH — لا دفعات هذا الشهر
    pays_this_month = Payment.objects.filter(
        date__year  = today.year,
        date__month = today.month,
    ).count()
    if pays_this_month == 0:
        _create(
            'NO_PAYS_THIS_MONTH', 'medium',
            'لا توجد دفعات هذا الشهر',
            f'لم يتم تسجيل أي دفعة في شهر {today.month}/{today.year}',
        )
    else:
        _resolve('NO_PAYS_THIS_MONTH')

    # 15. NEW_BENEFICIARY_24H — مستفيد جديد 24 ساعة
    new_benes = bene_qs.filter(date_joined__gte=now - timedelta(hours=24))
    for user in new_benes:
        hours = int((now - user.date_joined).total_seconds() / 3600)
        _create(
            'NEW_BENEFICIARY_24H', 'medium',
            f'مستفيد جديد — {user.get_full_name()}',
            f'انضم مستفيد جديد قبل {hours} ساعة',
            target_user = user,
            action_url  = '/admin-panel/requests/',
            extra_data  = {'hours': hours},
        )

    # 16. NEW_SPONSOR_24H — كافل جديد 24 ساعة
    new_sponsors = CustomUser.objects.filter(
        user_type   = 'sponsor',
        date_joined__gte = now - timedelta(hours=24),
    )
    for user in new_sponsors:
        hours = int((now - user.date_joined).total_seconds() / 3600)
        _create(
            'NEW_SPONSOR_24H', 'medium',
            f'كافل جديد — {user.get_full_name()}',
            f'انضم كافل جديد قبل {hours} ساعة',
            target_user = user,
            extra_data  = {'hours': hours},
        )

    # 17. USER_DISABLED_7D — تعطيل حساب آخر 7 أيام
    disabled_logs = ActivityLog.objects.filter(
        action      = 'DISABLE',
        created_at__gte = now - timedelta(days=7),
    )
    for log in disabled_logs:
        if log.target_id:
            try:
                user = CustomUser.objects.get(pk=log.target_id)
                days = (today - log.created_at.date()).days
                _create(
                    'USER_DISABLED_7D', 'medium',
                    f'حساب مُعطَّل — {user.get_full_name()}',
                    f'تم تعطيل الحساب منذ {days} يوم',
                    target_user = user,
                    extra_data  = {'days': days},
                )
            except (CustomUser.DoesNotExist, Exception):
                pass

    # 18. AIDS_DROP_50 — انخفاض المساعدات 50%
    last_month      = today.replace(day=1) - timedelta(days=1)
    aids_last_month = Aid.objects.filter(
        date__year  = last_month.year,
        date__month = last_month.month,
    ).count()
    if aids_last_month > 0 and aids_this_month < (aids_last_month * 0.5):
        drop = round((1 - aids_this_month / aids_last_month) * 100)
        _create(
            'AIDS_DROP_50', 'medium',
            f'انخفاض حاد في المساعدات ({drop}%)',
            f'انخفض عدد المساعدات {drop}% مقارنة بالشهر الماضي ({aids_this_month} vs {aids_last_month})',
            extra_data = {'drop': drop, 'this': aids_this_month, 'last': aids_last_month},
        )
    else:
        _resolve('AIDS_DROP_50')

    # 19. SPONSOR_CHANGED_7D — تغيير كافل آخر 7 أيام
    change_logs = ActivityLog.objects.filter(
        action      = 'UPDATE',
        description__icontains = 'تغيير كافل',
        created_at__gte        = now - timedelta(days=7),
    )
    for log in change_logs:
        if log.target_id:
            try:
                user = CustomUser.objects.get(pk=log.target_id)
                days = (today - log.created_at.date()).days
                _create(
                    'SPONSOR_CHANGED_7D', 'medium',
                    f'تغيير كافل — {user.get_full_name()}',
                    f'تم تغيير كافل هذا المستفيد منذ {days} يوم',
                    target_user = user,
                    extra_data  = {'days': days},
                )
            except (CustomUser.DoesNotExist, Exception):
                pass

    # ── 🟢 معلوماتية ──────────────────────────────

    # 20. ANNIVERSARY_1Y — ذكرى سنة على الاعتماد
    one_year_ago = today.replace(year=today.year - 1)
    for user in bene_qs.filter(date_joined__date=one_year_ago):
        _create(
            'ANNIVERSARY_1Y', 'info',
            f'ذكرى سنة — {user.get_full_name()}',
            f'مرت سنة كاملة على انضمام {user.get_full_name()} للمنصة 🎂',
            target_user = user,
        )

    # 21. NO_MSG_30D — لم يُرسَل له رسالة 30+ يوم
    for user in bene_qs.filter(is_active=True):
        last_msg = Notification.objects.filter(
            recipient = user,
            ntype     = 'NEW_MSG',
        ).order_by('-created_at').first()
        if last_msg:
            days = (now - last_msg.created_at).days
        else:
            days = (now - user.date_joined).days

        if days >= 30:
            _create(
                'NO_MSG_30D', 'info',
                f'بدون رسائل — {user.get_full_name()}',
                f'لم يتم إرسال أي رسالة لهذا المستفيد منذ {days} يوم' if last_msg
                else f'لم يتم إرسال أي رسالة لهذا المستفيد قط — انضم منذ {days} يوم',
                target_user = user,
                extra_data  = {'days': days},
            )
        else:
            _resolve('NO_MSG_30D', target_user=user)

    # 22. SPONSOR_5_BENE — كافل لديه 5+ مستفيدين
    for sp in SponsorProfile.objects.select_related('user').all():
        bene_count = 0
        for Model in [OrphanForm, FamilyForm, SpecialNeedsForm]:
            bene_count += Model.objects.filter(sponsor=sp).count()
        if bene_count >= 5:
            _create(
                'SPONSOR_5_BENE', 'info',
                f'كافل لديه {bene_count} مستفيدين — {sp.user.get_full_name()}',
                f'الكافل {sp.user.get_full_name()} يكفل {bene_count} مستفيدين — تأكد من قدرته',
                target_user = sp.user,
                extra_data  = {'count': bene_count},
            )
        else:
            _resolve('SPONSOR_5_BENE', target_user=sp.user)

    # 23. PENDING_COUNT_10 — 10+ طلبات معلّقة
    pending_total = CustomUser.objects.filter(
        is_approved=False
    ).exclude(user_type='admin').count()
    if pending_total >= 10:
        _create(
            'PENDING_COUNT_10', 'info',
            f'تراكم الطلبات المعلّقة ({pending_total})',
            f'يوجد {pending_total} طلب معلّق في انتظار المراجعة',
            action_url = '/admin-panel/requests/',
            extra_data = {'count': pending_total},
        )
    else:
        _resolve('PENDING_COUNT_10')

    # 24. END_MONTH_PENDING — آخر 3 أيام ودفعات معلّقة
    last_day  = calendar.monthrange(today.year, today.month)[1]
    days_left = last_day - today.day
    if days_left <= 3:
        pending_pays = Payment.objects.filter(
            status      = 'pending',
            date__year  = today.year,
            date__month = today.month,
        ).count()
        if pending_pays > 0:
            _create(
                'END_MONTH_PENDING', 'info',
                f'آخر {days_left} أيام و{pending_pays} دفعة معلّقة',
                f'ينتهي الشهر خلال {days_left} أيام ولا تزال هناك {pending_pays} دفعة معلّقة',
                extra_data = {'days_left': days_left, 'count': pending_pays},
            )
        else:
            _resolve('END_MONTH_PENDING')
    else:
        _resolve('END_MONTH_PENDING')

    # 25. MONTHLY_SUMMARY — ملخص أسبوعي كل إثنين
    if today.weekday() == 0:
        new_benes_week  = bene_qs.filter(date_joined__gte=now - timedelta(days=7)).count()
        pays_week_total = Payment.objects.filter(
            date__gte=today - timedelta(days=7)
        ).aggregate(s=Sum('amount_ils'))['s'] or 0
        aids_week = Aid.objects.filter(date__gte=today - timedelta(days=7)).count()
        _create(
            'MONTHLY_SUMMARY', 'info',
            f'ملخص الأسبوع — {today.strftime("%Y/%m/%d")}',
            f'مستفيدون جدد: {new_benes_week} | مدفوعات: {pays_week_total}₪ | مساعدات: {aids_week}',
            extra_data = {
                'new_benes': new_benes_week,
                'pays':      float(pays_week_total),
                'aids':      aids_week,
            },
        )


# ══════════════════════════════════════════════
#  Views
# ══════════════════════════════════════════════

@admin_required
def alerts_view(request):
    notif_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    return render(request, 'admin_panel/alerts.html', {
        'notif_count': notif_count,
    })


@admin_required
@require_GET
def alerts_data(request):
    """جلب التنبيهات مع الفلاتر"""
    # تشغيل المحرك أولاً
    try:
        run_smart_alerts()
    except Exception as e:
        pass  # لا نوقف الصفحة إذا فشل التحديث

    period    = request.GET.get('period',    'all')
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to',   '')
    status    = request.GET.get('status',    'active')
    level     = request.GET.get('level',     '')

    qs = SmartAlert.objects.select_related(
        'target_user', 'dismissed_by'
    ).filter(status=status)

    qs = _date_filter(qs, period, date_from, date_to, 'created_at')

    if level:
        qs = qs.filter(level=level)

    def _fmt(alert):
        return {
            'id':           alert.pk,
            'alert_type':   alert.alert_type,
            'level':        alert.level,
            'level_display':alert.get_level_display(),
            'level_color':  alert.level_color,
            'title':        alert.title,
            'message':      alert.message,
            'status':       alert.status,
            'action_url':   alert.action_url or '',
            'created_at': fmt_dt(alert.created_at),
            'target_user':  alert.target_user.get_full_name() if alert.target_user else '',
            'target_type':  alert.target_user_type_label if alert.target_user else '',
            'target_id':    str(alert.target_user.pk) if alert.target_user else '',
            'dismissed_by': (alert.dismissed_by.get_full_name() or alert.dismissed_by.username) if alert.dismissed_by else '',
            'dismissed_at': fmt_dt(alert.dismissed_at) if alert.dismissed_at else '',
        }

    alerts    = [_fmt(a) for a in qs.order_by('-created_at')]

    # إحصائيات
    all_active = SmartAlert.objects.filter(status='active')
    stats = {
        'active':   all_active.count(),
        'resolved': SmartAlert.objects.filter(status='resolved').count(),
        'critical': all_active.filter(level='critical').count(),
        'high':     all_active.filter(level='high').count(),
        'medium':   all_active.filter(level='medium').count(),
        'info':     all_active.filter(level='info').count(),
    }

    return JsonResponse({'alerts': alerts, 'stats': stats})


@admin_required
@require_POST
@csrf_protect
def dismiss_alert(request):
    """إغلاق تنبيه واحد"""
    alert_id = request.POST.get('alert_id', '').strip()
    if not alert_id:
        return JsonResponse({'status': 'error', 'message': 'معرف غير صالح'})
    try:
        alert = SmartAlert.objects.get(pk=alert_id)
        alert.dismiss(request.user)
        return JsonResponse({'status': 'success', 'message': 'تم إغلاق التنبيه'})
    except SmartAlert.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'التنبيه غير موجود'})


@admin_required
@require_POST
@csrf_protect
def dismiss_all_alerts(request):
    """إغلاق كل التنبيهات النشطة"""
    level = request.POST.get('level', '')
    qs    = SmartAlert.objects.filter(status='active')
    if level:
        qs = qs.filter(level=level)
    now   = timezone.now()
    count = qs.count()
    qs.update(
        status       = 'resolved',
        dismissed_by = request.user,
        dismissed_at = now,
    )
    return JsonResponse({
        'status':  'success',
        'message': f'تم إغلاق {count} تنبيه',
        'count':   count,
    })
def _resolve(alert_type, target_user=None):
    """إغلاق تلقائي عند حل المشكلة"""
    qs = SmartAlert.objects.filter(alert_type=alert_type, status='active')
    if target_user:
        qs = qs.filter(target_user=target_user)
    else:
        qs = qs.filter(target_user__isnull=True)
    qs.update(status='resolved', dismissed_at=timezone.now())