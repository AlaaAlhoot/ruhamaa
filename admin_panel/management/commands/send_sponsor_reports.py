"""
admin_panel/management/commands/send_sponsor_reports.py
أمر Django لإرسال تقارير الكفلاء الشهرية
"""

import io
import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'إرسال تقارير الكفلاء الشهرية تلقائياً'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',  type=int, default=None,
            help='سنة التقرير (افتراضي: الشهر الماضي)'
        )
        parser.add_argument(
            '--month', type=int, default=None,
            help='شهر التقرير (افتراضي: الشهر الماضي)'
        )
        parser.add_argument(
            '--sponsor-id', type=str, default=None,
            help='إرسال لكافل واحد فقط (UUID)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='تجربة بدون إرسال فعلي'
        )

    def handle(self, *args, **options):
        from core.models import CustomUser, SponsorReport
        from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm

        # تحديد الفترة
        today = date.today()
        if options['month'] and options['year']:
            year  = options['year']
            month = options['month']
        else:
            # الشهر الماضي
            if today.month == 1:
                year, month = today.year - 1, 12
            else:
                year, month = today.year, today.month - 1

        period_label = f'{month:02d}/{year}'
        dry_run      = options['dry_run']

        self.stdout.write(f'📋 إرسال تقارير {period_label} {"(تجريبي)" if dry_run else ""}')

        # جلب الكفلاء
        if options['sponsor_id']:
            sponsors = CustomUser.objects.filter(
                pk=options['sponsor_id'], user_type='sponsor', is_active=True
            )
        else:
            sponsors = CustomUser.objects.filter(
                user_type='sponsor', is_active=True
            ).exclude(email='')

        success = 0
        failed  = 0

        for sponsor in sponsors:
            try:
                result = _send_report(
                    sponsor      = sponsor,
                    year         = year,
                    month        = month,
                    period_label = period_label,
                    sent_by      = None,
                    is_auto      = True,
                    dry_run      = dry_run,
                )
                if result:
                    success += 1
                    self.stdout.write(self.style.SUCCESS(f'  ✅ {sponsor.get_full_name()} — {sponsor.email}'))
                else:
                    self.stdout.write(f'  ⏭️ {sponsor.get_full_name()} — تم الإرسال مسبقاً')
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {sponsor.get_full_name()} — {e}'))
                logger.error(f'فشل إرسال تقرير {sponsor.pk}: {e}')

        self.stdout.write(f'\n✅ نجح: {success} | ❌ فشل: {failed}')


def _build_report_context(sponsor, year, month, period_label, sender_label):
    """بناء بيانات التقرير"""
    from core.models import Payment, Aid, ActivityLog, Notification
    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm
    from django.utils import timezone as tz

    now   = tz.now()
    today = now.date()

    TYPE_LABELS = {'orphan': 'يتيم', 'family': 'أسرة', 'special': 'ذوو احتياجات'}
    AID_TYPES   = {
        'food': 'غذائية', 'medical': 'طبية', 'financial': 'مالية',
        'clothing': 'ملابس', 'furniture': 'أثاث', 'education': 'تعليمية', 'other': 'أخرى',
    }
    STATUS_MAP  = {'paid': 'مدفوعة', 'pending': 'معلّقة', 'late': 'متأخرة'}

    # جلب المكفولين
    bene_ids = set()
    for Model in [OrphanForm, FamilyForm, SpecialNeedsForm]:
        from sponsor.models import SponsorProfile
        try:
            sp_profile = SponsorProfile.objects.get(user=sponsor)
            ids = Model.objects.filter(sponsor=sp_profile).values_list('user_id', flat=True)
            bene_ids |= set(ids)
        except Exception:
            pass

    from core.models import CustomUser
    bene_users = CustomUser.objects.filter(pk__in=bene_ids)

    # إجماليات
    month_total_ils = 0
    all_total_ils   = 0
    total_aids      = 0
    beneficiaries   = []

    for user in bene_users:
        pays_qs = Payment.objects.filter(
            beneficiary=user, sponsor=sponsor
        ).order_by('-date')

        month_pays_qs = pays_qs.filter(date__year=year, date__month=month)
        month_pays    = month_pays_qs.aggregate(s=Sum('amount_ils'))['s'] or 0
        month_usd     = month_pays_qs.aggregate(s=Sum('amount_usd'))['s'] or 0
        total_pays    = pays_qs.aggregate(s=Sum('amount_ils'))['s'] or 0
        pays_count    = pays_qs.count()
        late_pays     = pays_qs.filter(status='late').count()
        last_pay      = pays_qs.first()

        aids_qs   = Aid.objects.filter(beneficiary=user).order_by('-date')
        aids_count= aids_qs.count()

        month_total_ils += float(month_pays)
        all_total_ils   += float(total_pays)
        total_aids      += aids_count

        beneficiaries.append({
            'full_name':     user.get_full_name(),
            'type_label':    TYPE_LABELS.get(user.user_type, ''),
            'reg_number':    user.registration_number or '—',
            'is_active':     user.is_active,
            'month_pays':    str(round(month_pays, 2)),
            'month_usd':     str(round(month_usd, 2)),
            'total_pays':    str(round(total_pays, 2)),
            'pays_count':    pays_count,
            'late_pays':     late_pays,
            'aids_count':    aids_count,
            'last_pay_date': str(last_pay.date) if last_pay else None,
            'payments': [{
                'date':       str(p.date),
                'amount_ils': str(p.amount_ils),
                'amount_usd': str(p.amount_usd),
                'status':     p.status,
                'note':       p.note or '',
            } for p in month_pays_qs[:10]],
            'aids': [{
                'date':          str(a.date),
                'name':          a.name,
                'aid_type_label':AID_TYPES.get(a.aid_type, a.aid_type),
                'quantity':      a.quantity,
                'provider':      a.provider,
            } for a in aids_qs.filter(date__year=year, date__month=month)[:10]],
        })

    # نشاط الكافل
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    login_count = ActivityLog.objects.filter(
        user=sponsor,
        action='LOGIN',
        created_at__gte=month_start,
    ).count() if hasattr(sponsor, 'user_type') else 0

    msg_count = Notification.objects.filter(
        sender=sponsor, ntype='NEW_MSG',
        created_at__gte=month_start,
    ).count()

    from core.utils import fmt_dt
    sponsor_activity = {
        'last_login':  fmt_dt(sponsor.last_login) if sponsor.last_login else 'لم يسجل دخولاً',
        'login_count': login_count,
        'msg_count':   msg_count,
    }

    return {
        'sponsor':          sponsor,
        'period_label':     period_label,
        'sender_label':     sender_label,
        'bene_count':       len(beneficiaries),
        'month_total_ils':  str(round(month_total_ils, 2)),
        'all_total_ils':    str(round(all_total_ils, 2)),
        'total_aids':       total_aids,
        'beneficiaries':    beneficiaries,
        'sponsor_activity': sponsor_activity,
    }


def _send_report(sponsor, year, month, period_label,
                 sent_by=None, is_auto=True, dry_run=False):
    """إرسال تقرير لكافل واحد"""
    import weasyprint
    import logging
    from core.models import SponsorReport
    logging.getLogger('weasyprint').setLevel(logging.ERROR)
    logging.getLogger('fontTools').setLevel(logging.ERROR)

    # تحقق هل أُرسل مسبقاً
    if SponsorReport.objects.filter(
        sponsor=sponsor, period_year=year, period_month=month
    ).exists():
        return False

    sender_label = 'النظام تلقائياً' if is_auto else (
        sent_by.get_full_name() or sent_by.username if sent_by else 'الإدارة'
    )

    # بناء البيانات
    context = _build_report_context(sponsor, year, month, period_label, sender_label)

    # توليد PDF
    html_content = render_to_string('admin_panel/sponsor_report_pdf.html', context)
    pdf_bytes    = weasyprint.HTML(string=html_content).write_pdf()

    # حفظ الملف
    from django.core.files.base import ContentFile
    pdf_content = ContentFile(pdf_bytes)
    fname       = f'report_{sponsor.pk}_{year}_{month:02d}.pdf'

    if dry_run:
        logger.info(f'[DRY RUN] سيُرسل لـ {sponsor.email} — {len(pdf_bytes)} bytes')
        return True

    # إرسال البريد
    subject = f'تقريركم الشهري — {period_label} — منصة رُحَمَاء'
    body    = f"""أخي الكريم {sponsor.get_full_name()} — حفظه الله،

السلام عليكم ورحمة الله وبركاته،

نُقدِّم لكم تقريركم الشهري لشهر {period_label} من منصة رُحَمَاء.
يتضمن التقرير المرفق بيانات مكفوليكم وآخر التحديثات المتعلقة بهم.

جزاكم الله خيراً على كفالتكم الكريمة.

مع تحيات،
فريق جمعية نسائم فلسطين الخيرية — منصة رُحَمَاء
"""
    email = EmailMessage(
        subject    = subject,
        body       = body,
        to         = [sponsor.email],
    )
    email.attach(fname, pdf_bytes, 'application/pdf')
    email.send(fail_silently=False)

    # حفظ السجل
    report = SponsorReport(
        sponsor      = sponsor,
        period_year  = year,
        period_month = month,
        is_auto      = is_auto,
        sent_by      = sent_by,
        status       = 'sent',
    )
    report.pdf_file.save(fname, pdf_content, save=False)
    report.save()

    return True
