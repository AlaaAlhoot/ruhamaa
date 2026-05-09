from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
import json

from core.models import CustomUser, ActivityLog, Notification
from core.utils import get_exchange_rates
from .decorators import admin_required

ARABIC_MONTHS = [
    'يناير','فبراير','مارس','أبريل','مايو','يونيو',
    'يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر',
]


def _pct(part, total):
    return round(part / total * 100) if total > 0 else 0


def _build_stats():
    """دالة مشتركة تُعيد كل الأرقام – تُستخدم في الصفحة والـ API."""
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from sponsor.models import PaymentReceipt, Announcement

    total_orphans  = OrphanForm.objects.count()
    total_specials = SpecialNeedsForm.objects.count()
    total_families = FamilyForm.objects.count()
    total_bene     = total_orphans + total_specials + total_families

    o_sp = OrphanForm.objects.filter(sponsor__isnull=False).count()
    s_sp = SpecialNeedsForm.objects.filter(sponsor__isnull=False).count()
    f_sp = FamilyForm.objects.filter(sponsor__isnull=False).count()
    sponsored   = o_sp + s_sp + f_sp
    unsponsored = total_bene - sponsored

    now = timezone.now()
    total_sponsors = CustomUser.objects.filter(
        user_type='sponsor', is_approved=True
    ).count()
    total_admins   = CustomUser.objects.filter(user_type='admin').count()
    new_sp_month   = CustomUser.objects.filter(
        user_type='sponsor', is_approved=True,
        date_joined__year=now.year, date_joined__month=now.month,
    ).count()
    pending_count = CustomUser.objects.filter(
        is_approved=False, is_active=True
    ).exclude(user_type='admin').count()

    approved_r = PaymentReceipt.objects.filter(status='موافق')
    pending_r  = PaymentReceipt.objects.filter(status='بانتظار المراجعة').count()
    rejected_r = PaymentReceipt.objects.filter(status='مرفوض').count()
    approved_c = approved_r.count()
    paid_s = float(approved_r.aggregate(t=Sum('amount_shekel'))['t'] or 0)
    paid_d = float(approved_r.aggregate(t=Sum('amount_dollar'))['t'] or 0)
    active_ann = Announcement.objects.filter(is_active=True).count()

    return dict(
        total_bene=total_bene,
        total_orphans=total_orphans, total_specials=total_specials,
        total_families=total_families,
        orphan_sponsored=o_sp, special_sponsored=s_sp, family_sponsored=f_sp,
        orphan_unsponsored=total_orphans - o_sp,
        special_unsponsored=total_specials - s_sp,
        family_unsponsored=total_families - f_sp,
        orphan_sponsored_pct=_pct(o_sp, total_orphans),
        special_sponsored_pct=_pct(s_sp, total_specials),
        family_sponsored_pct=_pct(f_sp, total_families),
        sponsored=sponsored, unsponsored=unsponsored,
        sponsored_pct=_pct(sponsored, total_bene),
        unsponsored_pct=_pct(unsponsored, total_bene),
        total_sponsors=total_sponsors, total_admins=total_admins,
        new_sponsors_this_month=new_sp_month,
        pending_count=pending_count,
        pending_receipts=pending_r, rejected_receipts=rejected_r,
        approved_count=approved_c,
        total_paid_shekel=paid_s, total_paid_dollar=paid_d,
        active_announcements=active_ann,
    )


@admin_required
def dashboard(request):
    from sponsor.models import PaymentReceipt, Message

    stats = _build_stats()
    rates = get_exchange_rates()
    now   = timezone.now()

    pending_users   = CustomUser.objects.filter(
        is_approved=False, is_active=True
    ).exclude(user_type='admin').order_by('-date_joined')[:5]

    latest_receipts = PaymentReceipt.objects.filter(
        status='بانتظار المراجعة'
    ).select_related('sponsor__user').order_by('-created_at')[:5]

    latest_logs     = ActivityLog.objects.select_related('user').order_by('-created_at')[:5]

    latest_messages = Message.objects.select_related(
        'sender', 'recipient'
    ).order_by('-created_at')[:5]

    notif_count     = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    unread_messages = Message.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    months_labels, chart_shekel, chart_dollar, chart_regs_sp = [], [], [], []
    for i in range(5, -1, -1):
        t       = now.replace(day=1) - timedelta(days=i * 28)
        m_start = t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_m  = 1 if m_start.month == 12 else m_start.month + 1
        next_y  = m_start.year + 1 if m_start.month == 12 else m_start.year
        m_end   = m_start.replace(year=next_y, month=next_m)
        months_labels.append(ARABIC_MONTHS[m_start.month - 1])
        chart_shekel.append(float(
            PaymentReceipt.objects.filter(
                status='موافق', created_at__gte=m_start, created_at__lt=m_end
            ).aggregate(t=Sum('amount_shekel'))['t'] or 0
        ))
        chart_dollar.append(float(
            PaymentReceipt.objects.filter(
                status='موافق', created_at__gte=m_start, created_at__lt=m_end
            ).aggregate(t=Sum('amount_dollar'))['t'] or 0
        ))
        chart_regs_sp.append(CustomUser.objects.filter(
            user_type='sponsor', date_joined__gte=m_start, date_joined__lt=m_end
        ).count())

    context = {
        **stats,
        'rates': rates,
        'notif_count': notif_count,
        'unread_messages': unread_messages,
        'pending_users': pending_users,
        'latest_receipts': latest_receipts,
        'latest_logs': latest_logs,
        'latest_messages': latest_messages,
        'chart_months':         json.dumps(months_labels, ensure_ascii=False),
        'chart_shekel':         json.dumps(chart_shekel),
        'chart_dollar':         json.dumps(chart_dollar),
        'chart_regs_sp':        json.dumps(chart_regs_sp),
        'chart_bene_dist':      json.dumps(
            [stats['total_orphans'], stats['total_specials'], stats['total_families']]
        ),
        'chart_receipt_status': json.dumps(
            [stats['approved_count'], stats['pending_receipts'], stats['rejected_receipts']]
        ),
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def dashboard_stats_api(request):
    """API – تُحدِّث الأرقام بدون إعادة تحميل الصفحة."""
    from sponsor.models import Message
    stats           = _build_stats()
    rates           = get_exchange_rates()
    notif_count     = Notification.objects.filter(recipient=request.user, is_read=False).count()
    unread_messages = Message.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({
        **stats,
        'notif_count':     notif_count,
        'unread_messages': unread_messages,
        'usd_to_ils':      rates['USD_TO_ILS'],
    })
