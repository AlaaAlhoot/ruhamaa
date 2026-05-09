"""
admin_panel/views/sponsor_report.py
تقارير الكفلاء الشهرية
"""

import io
from datetime import date

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.files.base import ContentFile

from core.models import CustomUser, Notification, Payment, Aid, SponsorReport
from core.utils import fmt_dt
from .decorators import admin_required
from ..management.commands.send_sponsor_reports import _send_report


# ══════════════════════════════════════════════
#  مساعدات
# ══════════════════════════════════════════════

def _get_sponsor_data(sponsor_user, year, month):
    """جمع بيانات الكافل للتقرير"""
    from beneficiary.models import OrphanForm, FamilyForm, SpecialNeedsForm
    from sponsor.models import SponsorProfile

    TYPE_LABELS = {'orphan': 'يتيم', 'family': 'أسرة', 'special': 'ذوو احتياجات'}
    AID_TYPES   = {
        'food': 'غذائية', 'medical': 'طبية', 'financial': 'مالية',
        'clothing': 'ملابس', 'furniture': 'أثاث', 'education': 'تعليمية', 'other': 'أخرى',
    }
    STATUS_MAP  = {'paid': 'مدفوعة', 'pending': 'معلّقة', 'late': 'متأخرة'}

    # بيانات الكافل
    try:
        sp_profile = SponsorProfile.objects.get(user=sponsor_user)
    except SponsorProfile.DoesNotExist:
        sp_profile = None

    # جلب المكفولين
    beneficiaries = []
    for Model in [OrphanForm, FamilyForm, SpecialNeedsForm]:
        try:
            forms = Model.objects.filter(
                sponsor=sp_profile
            ).select_related('user') if sp_profile else []
        except Exception:
            forms = []

        for form in forms:
            user = form.user

            # دفعات الشهر المحدد
            month_pays = Payment.objects.filter(
                beneficiary  = user,
                date__year   = year,
                date__month  = month,
            )
            month_ils = month_pays.aggregate(s=Sum('amount_ils'))['s'] or 0
            month_usd = month_pays.aggregate(s=Sum('amount_usd'))['s'] or 0

            # إجمالي الدفعات
            total_pays    = Payment.objects.filter(beneficiary=user)
            total_ils     = total_pays.aggregate(s=Sum('amount_ils'))['s'] or 0
            paid_count    = total_pays.filter(status='paid').count()
            pending_count = total_pays.filter(status='pending').count()
            late_count    = total_pays.filter(status='late').count()

            # آخر دفعة
            last_pay = total_pays.order_by('-date').first()

            # مساعدات الشهر
            month_aids = Aid.objects.filter(
                beneficiary = user,
                date__year  = year,
                date__month = month,
            )
            aids_list = [{
                'name':     a.name,
                'type':     AID_TYPES.get(a.aid_type, a.aid_type),
                'quantity': a.quantity,
                'provider': a.provider,
                'date':     str(a.date),
            } for a in month_aids]

            beneficiaries.append({
                'full_name':     user.get_full_name(),
                'id_number':     user.id_number or '—',
                'reg_number':    user.registration_number or '—',
                'type_label':    TYPE_LABELS.get(user.user_type, ''),
                'is_active':     user.is_active,
                'month_ils':     str(round(month_ils, 2)),
                'month_usd':     str(round(month_usd, 2)),
                'total_ils':     str(round(total_ils, 2)),
                'paid_count':    paid_count,
                'pending_count': pending_count,
                'late_count':    late_count,
                'last_pay':      str(last_pay.date) if last_pay else '—',
                'last_pay_status': STATUS_MAP.get(last_pay.status, '') if last_pay else '',
                'aids':          aids_list,
                'aids_count':    len(aids_list),
            })

    # إجمالي الكافل هذا الشهر
    all_bene_ids = [
        b['reg_number'] for b in beneficiaries
    ]
    total_month_ils = sum(float(b['month_ils']) for b in beneficiaries)
    total_month_usd = sum(float(b['month_usd']) for b in beneficiaries)
    total_all_ils   = sum(float(b['total_ils']) for b in beneficiaries)

    # نشاط الكافل
    login_logs = []
    from core.models import ActivityLog
    logs = ActivityLog.objects.filter(
        user         = sponsor_user,
        action       = 'LOGIN',
        created_at__year  = year,
        created_at__month = month,
    ).order_by('-created_at')
    login_count = logs.count()
    last_login  = sponsor_user.last_login

    # الرسائل المُرسَلة
    msgs_count = Notification.objects.filter(
        sender      = sponsor_user,
        ntype       = 'NEW_MSG',
        created_at__year  = year,
        created_at__month = month,
    ).count()

    import calendar
    month_names = {
        1:'يناير',2:'فبراير',3:'مارس',4:'أبريل',
        5:'مايو',6:'يونيو',7:'يوليو',8:'أغسطس',
        9:'سبتمبر',10:'أكتوبر',11:'نوفمبر',12:'ديسمبر',
    }

    return {
        'sponsor': {
            'full_name':    sponsor_user.get_full_name(),
            'email':        sponsor_user.email,
            'phone':        f'{sponsor_user.phone_country}{sponsor_user.phone}',
            'reg_number':   sponsor_user.registration_number or '—',
            'last_login':   fmt_dt(last_login) if last_login else '—',
            'login_count':  login_count,
            'msgs_count':   msgs_count,
            'job':          sp_profile.job if sp_profile else '—',
            'country':      sp_profile.country if sp_profile else '—',
        },
        'period': {
            'year':        year,
            'month':       month,
            'month_name':  month_names.get(month, ''),
            'label':       f'{month:02d}/{year}',
        },
        'summary': {
            'bene_count':      len(beneficiaries),
            'total_month_ils': str(round(total_month_ils, 2)),
            'total_month_usd': str(round(total_month_usd, 2)),
            'total_all_ils':   str(round(total_all_ils, 2)),
        },
        'beneficiaries': beneficiaries,
    }


def _generate_pdf(data, request):
    """توليد ملف PDF من البيانات"""
    import weasyprint
    import logging
    logging.getLogger('weasyprint').setLevel(logging.ERROR)
    logging.getLogger('fontTools').setLevel(logging.ERROR)

    html = render_to_string('admin_panel/sponsor_report_pdf.html', {
        'data':    data,
        'request': request,
    })
    return weasyprint.HTML(
        string   = html,
        base_url = request.build_absolute_uri('/'),
    ).write_pdf()


def _send_email(sponsor_user, pdf_bytes, data, sent_by=None, is_auto=False):
    """إرسال البريد مع المرفق"""
    period = data['period']
    name   = data['sponsor']['full_name']

    subject = f'تقرير كفالتك الشهري — {period["month_name"]} {period["year"]}'

    body = f"""بسم الله الرحمن الرحيم

أخي الكريم {name}،

السلام عليكم ورحمة الله وبركاته،

نُرفق لكم تقرير كفالتكم الشهري لشهر {period["month_name"]} {period["year"]}.

ملخص التقرير:
• عدد مكفوليكم: {data['summary']['bene_count']} مستفيد
• إجمالي مدفوعاتكم هذا الشهر: {data['summary']['total_month_ils']}₪
• إجمالي مدفوعاتكم منذ البداية: {data['summary']['total_all_ils']}₪

يمكنكم الاطلاع على تفاصيل المكفولين في الملف المرفق.

جزاكم الله خيراً على كرم عطائكم وسخاء دعمكم.

مع تحيات،
فريق جمعية نسائم فلسطين الخيرية — منصة رُحَمَاء"""

    email = EmailMessage(
        subject = subject,
        body    = body,
        to      = [sponsor_user.email],
    )
    fname = f'تقرير_كفالة_{name}_{period["label"].replace("/","_")}.pdf'
    email.attach(fname, pdf_bytes, 'application/pdf')
    email.send(fail_silently=False)

    # حفظ سجل الإرسال
    year  = period['year']
    month = period['month']

    # حذف السجل القديم إن وجد لنفس الشهر
    SponsorReport.objects.filter(
        sponsor      = sponsor_user,
        period_year  = year,
        period_month = month,
    ).delete()

    report = SponsorReport(
        sponsor      = sponsor_user,
        period_year  = year,
        period_month = month,
        is_auto      = is_auto,
        sent_by      = sent_by,
        status       = 'sent',
    )
    pdf_fname = f'report_{sponsor_user.pk}_{year}_{month:02d}.pdf'
    report.pdf_file.save(pdf_fname, ContentFile(pdf_bytes), save=True)
    return report


# ══════════════════════════════════════════════
#  Views
# ══════════════════════════════════════════════

@admin_required
@require_POST
@csrf_protect
def send_report(request):
    """إرسال تقرير لكافل واحد"""
    sponsor_id = request.POST.get('sponsor_id', '').strip()
    year       = int(request.POST.get('year',  date.today().year))
    month      = int(request.POST.get('month', date.today().month))

    if not sponsor_id:
        return JsonResponse({'status': 'error', 'message': 'معرف غير صالح'})

    try:
        sponsor_user = CustomUser.objects.get(pk=sponsor_id, user_type='sponsor')
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الكافل غير موجود'})

    if not sponsor_user.email:
        return JsonResponse({'status': 'error', 'message': 'لا يوجد بريد إلكتروني للكافل'})

    try:
        data      = _get_sponsor_data(sponsor_user, year, month)
        pdf_bytes = _generate_pdf(data, request)
        report    = _send_email(
            sponsor_user = sponsor_user,
            pdf_bytes    = pdf_bytes,
            data         = data,
            sent_by      = request.user,
            is_auto      = False,
        )
        return JsonResponse({
            'status':    'success',
            'message':   f'تم إرسال التقرير إلى {sponsor_user.email}',
            'report_id': report.pk,
        })
    except Exception as e:
        # حفظ سجل الفشل
        SponsorReport.objects.update_or_create(
            sponsor      = sponsor_user,
            period_year  = year,
            period_month = month,
            defaults={
                'is_auto':   False,
                'sent_by':   request.user,
                'status':    'failed',
                'error_msg': str(e),
            }
        )
        return JsonResponse({'status': 'error', 'message': f'فشل الإرسال: {str(e)}'})


@admin_required
@require_POST
@csrf_protect
def send_all_reports(request):
    """إرسال تقارير لجميع الكفلاء"""
    year  = int(request.POST.get('year',  date.today().year))
    month = int(request.POST.get('month', date.today().month))

    sponsors = CustomUser.objects.filter(
        user_type   = 'sponsor',
        is_active   = True,
        is_approved = True,
    ).exclude(email='')

    sent    = 0
    failed  = 0
    errors  = []

    for sponsor_user in sponsors:
        try:
            data      = _get_sponsor_data(sponsor_user, year, month)
            if not data['beneficiaries']:
                continue  # تجاهل الكفلاء بدون مكفولين
            pdf_bytes = _generate_pdf(data, request)
            _send_email(
                sponsor_user = sponsor_user,
                pdf_bytes    = pdf_bytes,
                data         = data,
                sent_by      = request.user,
                is_auto      = False,
            )
            sent += 1
        except Exception as e:
            failed += 1
            errors.append(f'{sponsor_user.get_full_name()}: {str(e)}')
            SponsorReport.objects.update_or_create(
                sponsor      = sponsor_user,
                period_year  = year,
                period_month = month,
                defaults={
                    'is_auto':   False,
                    'sent_by':   request.user,
                    'status':    'failed',
                    'error_msg': str(e),
                }
            )

    return JsonResponse({
        'status':  'success',
        'message': f'تم الإرسال: {sent} ✅ | فشل: {failed} ❌',
        'sent':    sent,
        'failed':  failed,
        'errors':  errors,
    })


@admin_required
@require_GET
def report_history(request):
    """سجل الإرسال"""
    sponsor_id = request.GET.get('sponsor_id', '').strip()

    qs = SponsorReport.objects.select_related(
        'sponsor', 'sent_by'
    ).order_by('-sent_at')

    if sponsor_id:
        qs = qs.filter(sponsor_id=sponsor_id)

    return JsonResponse({'reports': [{
        'id':           r.pk,
        'sponsor':      r.sponsor.get_full_name(),
        'sponsor_id':   str(r.sponsor.pk),
        'period':       r.period_label,
        'period_year':  r.period_year,
        'period_month': r.period_month,
        'sent_at':      fmt_dt(r.sent_at),
        'sender':       r.sender_label,
        'is_auto':      r.is_auto,
        'status':       r.status,
        'status_label': r.get_status_display(),
        'error_msg':    r.error_msg or '',
        'has_pdf':      bool(r.pdf_file),
    } for r in qs]})


@admin_required
@require_GET
def view_report(request, report_id):
    """فتح ملف PDF التقرير"""
    try:
        report = SponsorReport.objects.get(pk=report_id)
    except SponsorReport.DoesNotExist:
        return HttpResponse('التقرير غير موجود', status=404)

    if not report.pdf_file:
        return HttpResponse('الملف غير موجود', status=404)

    return FileResponse(
        report.pdf_file.open('rb'),
        content_type        = 'application/pdf',
        as_attachment       = False,
        filename            = f'report_{report.period_label.replace("/","_")}.pdf',
    )


@admin_required
@require_GET
def preview_report(request):
    """معاينة التقرير قبل الإرسال"""
    sponsor_id = request.GET.get('sponsor_id', '').strip()
    year       = int(request.GET.get('year',  date.today().year))
    month      = int(request.GET.get('month', date.today().month))

    try:
        sponsor_user = CustomUser.objects.get(pk=sponsor_id, user_type='sponsor')
        data         = _get_sponsor_data(sponsor_user, year, month)
        html         = render_to_string('admin_panel/sponsor_report_pdf.html', {
            'data':    data,
            'request': request,
        })
        return HttpResponse(html)
    except CustomUser.DoesNotExist:
        return HttpResponse('الكافل غير موجود', status=404)
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, FileResponse, Http404
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect

from core.models import CustomUser, SponsorReport
from .decorators import admin_required
from ..management.commands import send_sponsor_reports


@admin_required
@require_POST
@csrf_protect
def send_report(request):
    """إرسال تقرير يدوي لكافل واحد"""
    sponsor_id = request.POST.get('sponsor_id', '').strip()
    month      = int(request.POST.get('month', 0))
    year       = int(request.POST.get('year',  0))

    if not sponsor_id or not month or not year:
        return JsonResponse({'status': 'error', 'message': 'بيانات ناقصة'})

    try:
        sponsor = CustomUser.objects.get(pk=sponsor_id, user_type='sponsor')
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'الكافل غير موجود'})

    period_label = f'{month:02d}/{year}'

    try:
        result = _send_report(
            sponsor      = sponsor,
            year         = year,
            month        = month,
            period_label = period_label,
            sent_by      = request.user,
            is_auto      = False,
        )
        if result:
            return JsonResponse({'status': 'success', 'message': f'تم إرسال تقرير {period_label} بنجاح'})
        else:
            return JsonResponse({'status': 'error', 'message': f'تقرير {period_label} أُرسل مسبقاً'})
    except Exception as e:
        # حفظ سجل الفشل
        SponsorReport.objects.create(
            sponsor      = sponsor,
            period_year  = year,
            period_month = month,
            is_auto      = False,
            sent_by      = request.user,
            status       = 'failed',
            error_msg    = str(e),
        )
        return JsonResponse({'status': 'error', 'message': f'فشل الإرسال: {str(e)}'})


@admin_required
@require_POST
@csrf_protect
def send_all_reports(request):
    """إرسال تقارير لجميع الكفلاء"""
    month = int(request.POST.get('month', 0))
    year  = int(request.POST.get('year',  0))

    if not month or not year:
        return JsonResponse({'status': 'error', 'message': 'بيانات ناقصة'})

    sponsors     = CustomUser.objects.filter(
        user_type='sponsor', is_active=True
    ).exclude(email='')
    period_label = f'{month:02d}/{year}'
    success = 0
    failed  = 0
    skipped = 0

    for sponsor in sponsors:
        try:
            result = _send_report(
                sponsor      = sponsor,
                year         = year,
                month        = month,
                period_label = period_label,
                sent_by      = request.user,
                is_auto      = False,
            )
            if result:
                success += 1
            else:
                skipped += 1
        except Exception as e:
            failed += 1
            SponsorReport.objects.get_or_create(
                sponsor      = sponsor,
                period_year  = year,
                period_month = month,
                defaults={
                    'is_auto':   False,
                    'sent_by':   request.user,
                    'status':    'failed',
                    'error_msg': str(e),
                }
            )

    return JsonResponse({
        'status':  'success',
        'message': f'نجح: {success} | فشل: {failed} | مكرر: {skipped}',
        'success': success,
        'failed':  failed,
        'skipped': skipped,
    })


@admin_required
@require_GET
def report_history(request):
    """سجل التقارير المرسلة لكافل"""
    sponsor_id = request.GET.get('sponsor_id', '').strip()
    if not sponsor_id:
        return JsonResponse({'status': 'error', 'message': 'معرف غير صالح'})

    from core.utils import fmt_dt
    reports = SponsorReport.objects.filter(
        sponsor_id=sponsor_id
    ).select_related('sent_by').order_by('-sent_at')

    return JsonResponse({'reports': [{
        'id':           r.pk,
        'period_label': r.period_label,
        'sent_at':      fmt_dt(r.sent_at),
        'is_auto':      r.is_auto,
        'sent_by':      (r.sent_by.get_full_name() or r.sent_by.username) if r.sent_by else '',
        'status':       r.status,
        'error_msg':    r.error_msg or '',
        'has_file':     bool(r.pdf_file),
    } for r in reports]})


@admin_required
@require_GET
def view_report(request, pk):
    """فتح ملف PDF التقرير"""
    try:
        report = SponsorReport.objects.get(pk=pk)
        if not report.pdf_file:
            raise Http404('الملف غير موجود')
        return FileResponse(
            report.pdf_file.open('rb'),
            content_type='application/pdf',
            filename=f'report_{report.period_label.replace("/","_")}.pdf',
        )
    except SponsorReport.DoesNotExist:
        raise Http404('التقرير غير موجود')