# ==================== main/views.py ====================
import os
import re
import html
import json
import logging
import traceback
from pathlib import Path
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db import transaction

from core.models import (
    CustomUser, OTPVerification, Notification,
    Complaint, FAQ
)
from core.utils import (
    get_client_ip, log_activity, send_otp_email,
    create_notification, notify_admins, get_countries,
    get_exchange_rates, compress_image, send_approval_email
)
from core.validators import (
    validate_id_number, validate_arabic_text,
    validate_upload_file
)
from beneficiary.models import (
    JOBS, OrphanForm, OrphanMother, OrphanFather,
    SpecialNeedsForm, FamilyForm, FamilyWife,
    CurrentGuardian, FamilyMember,
    OrphanDocument, SpecialDocument, FamilyDocument
)
from sponsor.models import SponsorProfile


logger = logging.getLogger(__name__)


# ============================================================
# الصفحة الرئيسية
# ============================================================

def home_view(request):
    import hashlib
    from datetime import date
    from django.core.cache import cache
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    from core.models import SystemSettings  # أو المسار الصحيح عندك

    # ── إحصائيات (مُخزَّنة 5 دقائق) ──
    stats = cache.get('home_stats_v2')
    if not stats:
        stats = {
            'total_orphans':  OrphanForm.objects.count(),
            'father_orphans': OrphanForm.objects.filter(orphan_type='أب').count(),
            'mother_orphans': OrphanForm.objects.filter(orphan_type='أم').count(),
            'both_orphans':   OrphanForm.objects.filter(orphan_type='كلاهما').count(),
            'special_needs':  SpecialNeedsForm.objects.count(),
            'families':       FamilyForm.objects.count(),
            'sponsors':       CustomUser.objects.filter(
                                  user_type='sponsor', is_approved=True).count(),
            'total_benefits': (
                OrphanForm.objects.count() +
                SpecialNeedsForm.objects.count() +
                FamilyForm.objects.count()
            ),
        }
        cache.set('home_stats_v2', stats, timeout=300)

    # ── اختيار القصص اليومية (seed = تاريخ اليوم) ──
    today_seed = int(hashlib.md5(str(date.today()).encode()).hexdigest(), 16)

    def pick_daily(qs, seed_offset=0):
        """اختر سجلاً واحداً بشكل شبه عشوائي يتغير كل 24 ساعة"""
        ids = list(qs.values_list('id', flat=True).order_by('id'))
        if not ids:
            return None
        idx = (today_seed + seed_offset) % len(ids)
        chosen_id = ids[idx]
        return qs.get(id=chosen_id)

    # الأيتام غير المكفولين (sponsor IS NULL أو status != 'تم التكفل')
    orphan_qs = OrphanForm.objects.filter(
        sponsor__isnull=True
    ).exclude(status='تم التكفل')

    # ذوو الاحتياجات غير المكفولين
    special_qs = SpecialNeedsForm.objects.filter(
        sponsor__isnull=True
    )

    # الأسر غير المكفولة
    family_qs = FamilyForm.objects.filter(
        sponsor__isnull=True
    )

    # اختيار قصة من كل نوع — إن لم توجد يُستبدل بأي غير مكفول
    def get_story(primary_qs, fallback_qs_list, seed_offset):
        story = pick_daily(primary_qs, seed_offset)
        if story:
            return story
        # fallback: أي غير مكفول من الأنواع الأخرى
        for fqs in fallback_qs_list:
            story = pick_daily(fqs, seed_offset + 100)
            if story:
                return story
        return None

    orphan_story  = get_story(orphan_qs,  [special_qs, family_qs],  seed_offset=0)
    family_story  = get_story(family_qs,  [orphan_qs, special_qs],  seed_offset=1)
    special_story = get_story(special_qs, [orphan_qs, family_qs],   seed_offset=2)

    # ── إعدادات النظام للفوتر ──
    try:
        footer_address = SystemSettings.get('address', '')
        footer_hours   = SystemSettings.get('working_hours', '')
    except Exception:
        footer_address = ''
        footer_hours   = ''

    return render(request, 'main/home.html', {
        'stats':         stats,
        'stories': {
            'orphan':  orphan_story,
            'family':  family_story,
            'special': special_story,
        },
        'footer_address': footer_address,
        'footer_hours':   footer_hours,
    })


# ============================================================
# تواصل معنا
# ============================================================

@csrf_protect
@require_POST
def contact_view(request):
    name          = request.POST.get('name',          '').strip()
    phone         = request.POST.get('phone',         '').strip()
    phone_country = request.POST.get('phone_country', '+970').strip()
    email         = request.POST.get('email',         '').strip()
    subject       = request.POST.get('subject',       '').strip()
    message       = request.POST.get('message',       '').strip()
    ip            = get_client_ip(request)
    errors        = {}

    if not name or len(name) > 100:
        errors['name']    = 'الاسم مطلوب ولا يتجاوز 100 حرف'
    if not phone:
        errors['phone']   = 'رقم التواصل مطلوب'
    if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        errors['email']   = 'البريد الإلكتروني غير صالح'
    if not subject or len(subject) > 200:
        errors['subject'] = 'العنوان مطلوب ولا يتجاوز 200 حرف'
    if not message or len(message) > 700:
        errors['message'] = 'الرسالة مطلوبة ولا تتجاوز 700 حرف'

    for val in [name, subject, message]:
        if re.search(r'<script|javascript:|onerror=', val, re.I):
            return JsonResponse({'status': 'error', 'message': 'مدخل غير صالح'}, status=400)

    if errors:
        return JsonResponse({'status': 'error', 'errors': errors})

    Complaint.objects.create(
        name          = name,
        phone         = phone,
        phone_country = phone_country,
        email         = email,
        subject       = subject,
        message       = message,
        ip_address    = ip,
    )

    notify_admins(
        ntype      = 'SYSTEM',
        title      = 'رسالة تواصل جديدة 📩',
        message    = f'رسالة من {name} — {subject}',
        action_url = '/admin-panel/complaints/',
    )

    return JsonResponse({'status': 'success', 'message': 'تم إرسال رسالتك بنجاح ✅'})


# ============================================================
# تسجيل الدخول
# ============================================================

@require_http_methods(['GET', 'POST'])
@csrf_protect
def login_view(request):

    if request.user.is_authenticated:
        return _redirect_by_type(request.user)

    if request.method == 'GET':
        return render(request, 'main/login.html')

    # ── تحقق AJAX ──
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'طلب غير صالح'}, status=400)

    ip          = get_client_ip(request)
    lockout_key = f'login_lock_{ip}'
    attempt_key = f'login_att_{ip}'

    # ── Honeypot ──
    if request.POST.get('honeypot', ''):
        log_activity(None, 'BLOCKED',
                     description=f'Honeypot triggered — IP: {ip}',
                     request=request)
        return JsonResponse({'status': 'error', 'message': 'غير مسموح'})

    # ── Rate Limiting ──
    if cache.get(lockout_key):
        return JsonResponse({
            'status':    'locked',
            'message':   'تم تجميد الدخول لمدة 2 دقيقة بسبب المحاولات المتكررة',
            'remaining': 120,
        }, status=429)

    # ── استخراج المدخلات ──
    identifier = request.POST.get('identifier', '').strip()
    password   = request.POST.get('password',   '').strip()

    # ── حماية من الحقن ──
    INJECT_PATTERN = re.compile(
        r'(<script|javascript:|onerror=|onload=|data:text/html)', re.I
    )
    if INJECT_PATTERN.search(identifier) or INJECT_PATTERN.search(password):
        log_activity(None, 'BLOCKED',
                     description=f'محاولة حقن — IP: {ip}',
                     request=request)
        return JsonResponse({'status': 'error', 'message': 'مدخل غير صالح'}, status=400)

    if re.search(r'[<>\'";\-\-\/\*\\]', identifier) or len(identifier) > 150:
        return JsonResponse({
            'status':  'error',
            'message': 'مدخل غير صالح',
            'errors':  {'identifier': 'مدخل غير صالح'},
        })

    # ── تحقق الحقول ──
    if not identifier:
        return JsonResponse({
            'status': 'error',
            'errors': {'identifier': 'اسم المستخدم أو رقم الهوية مطلوب'},
        })
    if not password:
        return JsonResponse({
            'status': 'error',
            'errors': {'password': 'كلمة المرور مطلوبة'},
        })
    if len(password) < 4 or len(password) > 128:
        return JsonResponse({
            'status': 'error',
            'errors': {'password': 'كلمة المرور غير صالحة'},
        })

    # ── جلب حد المحاولات من الإعدادات ──
    try:
        from core.models import SystemSettings
        max_attempts = int(SystemSettings.get('max_login_attempts', '5') or '5')
        max_attempts = max(1, min(max_attempts, 20))  # بين 1 و20
    except Exception:
        max_attempts = 5

    # ── البحث عن المستخدم ──
    user_obj = None
    try:
        user_obj = CustomUser.objects.get(username=identifier)
    except CustomUser.DoesNotExist:
        try:
            if re.match(r'^[9847]\d{8}$', identifier):
                user_obj = CustomUser.objects.get(id_number=identifier)
        except CustomUser.DoesNotExist:
            pass

    # ── المصادقة ──
    auth_user = authenticate(
        request,
        username = user_obj.username if user_obj else '__invalid__',
        password = password,
    ) if user_obj else None

    # ── فشل الدخول ──
    if auth_user is None:
        attempts = cache.get(attempt_key, 0) + 1
        cache.set(attempt_key, attempts, 120)

        if attempts >= max_attempts:
            cache.set(lockout_key, True, 120)
            cache.delete(attempt_key)
            log_activity(
                None, 'BLOCKED',
                description=f'حظر IP بعد {max_attempts} محاولات فاشلة — {ip}',
                request=request,
            )
            return JsonResponse({
                'status':    'locked',
                'message':   f'تم تجميد الدخول 2 دقيقة بعد {max_attempts} محاولات فاشلة',
                'remaining': 120,
            }, status=429)

        log_activity(
            None, 'FAILED_LOGIN',
            description=f'محاولة دخول فاشلة — {identifier} — IP: {ip}',
            request=request,
        )
        return JsonResponse({
            'status':        'error',
            'message':       'اسم المستخدم أو كلمة المرور غير صحيحة',
            'attempts_left': max_attempts - attempts,
            'errors':        {'identifier': 'بيانات الدخول غير صحيحة'},
        })

    # ── تحقق حالة الحساب ──
    if not auth_user.is_active:
        return JsonResponse({
            'status':  'error',
            'message': 'حسابك موقوف — تواصل مع الإدارة',
        })

    if not auth_user.is_approved and not auth_user.is_superuser:
        return JsonResponse({
            'status':  'error',
            'message': 'حسابك قيد المراجعة — سيتم إشعارك فور الموافقة',
        })

    # ── تحقق وضع الصيانة ──
    try:
        from core.models import SystemSettings
        if SystemSettings.get('maintenance_mode', 'false') == 'true':
            if getattr(auth_user, 'user_type', '') != 'admin' and not auth_user.is_superuser:
                return JsonResponse({
                    'status':  'error',
                    'message': 'الموقع تحت الصيانة — يُسمح فقط للأدمن بالدخول',
                })
    except Exception:
        pass

    # ── تسجيل الدخول ──
    login(request, auth_user)

    # ── إعداد الجلسة ──
    remember_me = request.POST.get('remember_me', '') == 'on'
    if remember_me:
        request.session.set_expiry(24 * 60 * 60)  # يوم كامل
    else:
        try:
            from core.models import SystemSettings
            timeout_min = int(SystemSettings.get('session_timeout', '180') or '180')
            timeout_min = max(5, min(timeout_min, 1440))  # بين 5 دقائق ويوم
            request.session.set_expiry(timeout_min * 60)
        except Exception:
            request.session.set_expiry(3 * 60 * 60)  # 3 ساعات افتراضي

    cache.delete(attempt_key)
    cache.delete(lockout_key)

    auth_user.login_count   = (auth_user.login_count or 0) + 1
    auth_user.last_login_ip = ip
    auth_user.last_login    = timezone.now()
    auth_user.save(update_fields=['login_count', 'last_login_ip', 'last_login'])

    log_activity(
        auth_user, 'LOGIN',
        description=f'دخول ناجح — {auth_user.user_type} — IP: {ip}',
        request=request,
    )

    return JsonResponse({
        'status':   'success',
        'message':  f'أهلاً {auth_user.first_name} 👋',
        'redirect': _redirect_by_type(auth_user, url_only=True),
    })


# ============================================================
# تسجيل الخروج
# ============================================================

@login_required(login_url='/login/')
def logout_view(request):
    log_activity(request.user, 'LOGOUT',
                 description='تسجيل خروج', request=request)
    logout(request)
    return redirect('/login/')


# ============================================================
# التسجيل — register_view (مدمجة مع _handle_register)
# ============================================================

@require_http_methods(['GET', 'POST'])
@csrf_protect
def register_view(request):

    if request.user.is_authenticated:
        return redirect('/')

    if request.method == 'GET':
        return render(request, 'main/register.html', {'jobs': JOBS})

    # ── تحقق AJAX ──────────────────────────────────────────
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'طلب غير صالح'}, status=400)

    # ── Honeypot ────────────────────────────────────────────
    if request.POST.get('honeypot', ''):
        return JsonResponse({'status': 'error', 'message': 'غير مسموح'})

    # ── Rate Limiting ───────────────────────────────────────
    ip          = get_client_ip(request)
    lockout_key = f'reg_lock_{ip}'
    attempt_key = f'reg_att_{ip}'

    if cache.get(lockout_key):
        return JsonResponse({
            'status':    'locked',
            'message':   'تم تجميد التسجيل مؤقتاً، حاول بعد 5 دقائق',
            'remaining': 300,
        }, status=429)

    data  = request.POST
    files = request.FILES

    # ── نوع الحساب ──────────────────────────────────────────
    user_type = data.get('user_type', '').strip()
    if user_type not in ['sponsor', 'orphan', 'family', 'special']:
        return JsonResponse({'status': 'error', 'message': 'نوع الحساب غير صالح'})

    errors = {}

    # ── الاسم الرباعي ────────────────────────────────────────
    name_fields = [
        ('first_name',  'الاسم الأول'),
        ('father_name', 'اسم الأب'),
        ('grand_name',  'اسم الجد'),
        ('family_name', 'اسم العائلة'),
    ]
    for field, label in name_fields:
        val = data.get(field, '').strip()
        if not val:
            errors[field] = f'{label} مطلوب'
        elif len(val) > 50:
            errors[field] = f'{label} لا يتجاوز 50 حرفاً'
        else:
            try:
                validate_arabic_text(val)
            except Exception as e:
                errors[field] = str(e)

    first_name  = data.get('first_name',  '').strip()
    father_name = data.get('father_name', '').strip()
    grand_name  = data.get('grand_name',  '').strip()
    family_name = data.get('family_name', '').strip()

    # ── الجنس ───────────────────────────────────────────────
    gender = data.get('gender', '').strip()
    if not gender or gender not in ['ذكر', 'أنثى']:
        errors['gender'] = 'الجنس مطلوب'

    # ── الجنسية ─────────────────────────────────────────────
    nationality      = data.get('nationality',      'فلسطينية').strip()
    nationality_code = data.get('nationality_code', 'PS').strip()

    # ── البريد الإلكتروني ────────────────────────────────────
    email = data.get('email', '').strip().lower()
    if not email:
        errors['email'] = 'البريد الإلكتروني مطلوب'
    elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        errors['email'] = 'البريد الإلكتروني غير صالح'
    elif re.search(r"[<>\"';]", email):
        errors['email'] = 'البريد الإلكتروني يحتوي على رموز غير مسموح بها'
    elif CustomUser.objects.filter(email=email).exists():
        errors['email'] = 'البريد الإلكتروني مستخدم مسبقاً'

    # ── رقم الجوال الأول ─────────────────────────────────────
    phone1         = data.get('phone1', '').strip()
    phone1_country = data.get('phone1_country', '+970').strip()
    if not phone1:
        errors['phone1'] = 'رقم الجوال مطلوب'
    elif not re.match(r'^\d{7,15}$', phone1):
        errors['phone1'] = 'رقم الجوال غير صالح'
    elif _phone_exists_anywhere(phone1):
        errors['phone1'] = 'رقم الجوال مستخدم مسبقاً في النظام'

    # ── رقم الجوال الثاني (اختياري) ──────────────────────────
    phone2         = data.get('phone2', '').strip()
    phone2_country = data.get('phone2_country', '+970').strip()
    if phone2:
        if not re.match(r'^\d{7,15}$', phone2):
            errors['phone2'] = 'رقم الجوال الثاني غير صالح'
        elif phone2 == phone1:
            errors['phone2'] = 'رقم الجوال الثاني يجب أن يختلف عن الأول'
        elif _phone_exists_anywhere(phone2):
            errors['phone2'] = 'رقم الجوال الثاني مستخدم مسبقاً في النظام'

    # ── رقم الواتساب ─────────────────────────────────────────
    whatsapp         = data.get('whatsapp', '').strip()
    whatsapp_country = data.get('whatsapp_country', '+970').strip()
    if not whatsapp:
        errors['whatsapp'] = 'رقم الواتساب مطلوب'
    elif not re.match(r'^\d{7,15}$', whatsapp):
        errors['whatsapp'] = 'رقم الواتساب غير صالح'
    elif _whatsapp_exists_anywhere(whatsapp):
        errors['whatsapp'] = 'رقم الواتساب مستخدم مسبقاً'

    # ── كلمة المرور ──────────────────────────────────────────
    password  = data.get('password',  '')
    password2 = data.get('password2', '')
    if not password:
        errors['password'] = 'كلمة المرور مطلوبة'
    elif len(password) < 8:
        errors['password'] = 'كلمة المرور يجب أن تكون 8 أحرف على الأقل'
    elif not re.search(r'\d', password):
        errors['password'] = 'كلمة المرور يجب أن تحتوي على رقم'
    elif len(password) > 128:
        errors['password'] = 'كلمة المرور طويلة جداً'
    if password and password != password2:
        errors['password2'] = 'كلمتا المرور غير متطابقتان'

    # ── تحقق حسب النوع ───────────────────────────────────────
    username  = ''
    id_number = ''

    if user_type == 'sponsor':
        # اسم المستخدم
        username = data.get('username', '').strip()
        if not username:
            errors['username'] = 'اسم المستخدم مطلوب'
        elif len(username) < 4:
            errors['username'] = 'اسم المستخدم يجب أن يكون 4 أحرف على الأقل'
        elif len(username) > 50:
            errors['username'] = 'اسم المستخدم لا يتجاوز 50 حرفاً'
        elif re.search(r'[<>\'";\-\-\/\*\\\s]', username):
            errors['username'] = 'اسم المستخدم يحتوي على رموز غير مسموح بها'
        elif CustomUser.objects.filter(username=username).exists():
            errors['username'] = 'اسم المستخدم مستخدم مسبقاً'

        # المهنة والدولة والمدينة
        job     = data.get('job',     '').strip()
        country = data.get('country', '').strip()
        city    = data.get('city',    '').strip()
        if not job:     errors['job']     = 'المهنة مطلوبة'
        if not country: errors['country'] = 'الدولة مطلوبة'
        if not city:    errors['city']    = 'المدينة مطلوبة'

        # الصورة (اختيارية للكافل لكن نتحقق من الحجم والنوع إن وُجدت)
        if 'photo' in files:
            try:
                validate_upload_file(files['photo'])
            except Exception as e:
                errors['photo'] = str(e)

    else:
        # رقم الهوية للمستفيدين
        id_number = data.get('id_number', '').strip()
        if not id_number:
            errors['id_number'] = 'رقم الهوية مطلوب'
        else:
            try:
                validate_id_number(id_number)
            except Exception as e:
                errors['id_number'] = str(e)
            else:
                if _id_exists_anywhere(id_number):
                    errors['id_number'] = 'رقم الهوية مسجّل مسبقاً في النظام'

        # تحقق من صورة المستفيد (إلزامية)
        if 'photo' in files:
            try:
                validate_upload_file(files['photo'])
            except Exception as e:
                errors['photo'] = str(e)
        else:
            errors['photo'] = 'الصورة الشخصية مطلوبة'

        # تحقق الحقول الخاصة بكل نوع
        if user_type == 'orphan':
            _validate_orphan_fields(data, files, errors)
        elif user_type == 'special':
            _validate_special_fields(data, files, errors)
        elif user_type == 'family':
            _validate_family_fields(data, files, errors)

    # ── إرجاع الأخطاء ────────────────────────────────────────
    if errors:
        return JsonResponse({
            'status':  'error',
            'errors':  errors,
            'message': 'يرجى تصحيح الأخطاء الموضحة',
        })

    # ── Rate Limiting — زيادة المحاولات ──────────────────────
    attempts = cache.get(attempt_key, 0) + 1
    cache.set(attempt_key, attempts, 600)
    if attempts >= 10:
        cache.set(lockout_key, True, 600)
        cache.delete(attempt_key)

    # ── إنشاء المستخدم والبيانات ──────────────────────────────
    try:
        with transaction.atomic():

            # اسم المستخدم للمستفيدين يُبنى من النوع + رقم الهوية
            if user_type != 'sponsor':
                username = f'{user_type}_{id_number}'

            user = CustomUser(
                username         = username,
                email            = email,
                first_name       = first_name,
                father_name      = father_name,
                grand_name       = grand_name,
                family_name      = family_name,
                user_type        = user_type,
                nationality      = nationality,
                nationality_code = nationality_code,
                gender           = gender,
                phone            = phone1,
                phone_country    = phone1_country,
                whatsapp         = whatsapp,
                whatsapp_country = whatsapp_country,
                is_approved      = False,
                is_active        = True,
            )
            if user_type != 'sponsor':
                user.id_number = id_number
            user.set_password(password)
            user.save()

            # ── كافل ────────────────────────────────────────
            if user_type == 'sponsor':
                type_label = _register_sponsor(user, data, files)

            # ── يتيم ────────────────────────────────────────
            elif user_type == 'orphan':
                type_label = _register_orphan(user, data, files)

            # ── ذوو احتياجات ─────────────────────────────────
            elif user_type == 'special':
                type_label = _register_special(user, data, files)

            # ── أسرة ─────────────────────────────────────────
            elif user_type == 'family':
                type_label = _register_family(user, data, files)

            # إشعار الأدمن
            notify_admins(
                ntype      = 'NEW_USER',
                title      = 'طلب تسجيل جديد 📋',
                message    = f'{user.get_full_name()} — {type_label}',
                sender     = user,
                action_url = '/admin-panel/requests/',
            )
            log_activity(
                user, 'REGISTER',
                description = f'تسجيل حساب جديد — {type_label}',
                request     = request,
            )

            # مسح محاولات التسجيل عند النجاح
            cache.delete(attempt_key)

            return JsonResponse({
                'status':     'pending',
                'message':    'تم إرسال طلبك بنجاح، سيتم مراجعته وإشعارك',
                'name':       user.first_name,
                'type_label': type_label,
            })

    except Exception as e:
        logger.error(traceback.format_exc())
        err = str(e).lower()

        if 'data too long' in err:
            msg = 'أحد الحقول يحتوي على بيانات طويلة جداً'
        elif 'duplicate entry' in err or 'unique' in err:
            msg = 'هذه البيانات مسجّلة مسبقاً في النظام'
        elif 'not null' in err or 'cannot be null' in err:
            msg = 'يرجى ملء جميع الحقول المطلوبة'
        elif 'whatsapp' in err:
            msg = 'رقم الواتساب غير صالح'
        elif 'phone' in err:
            msg = 'رقم الجوال غير صالح'
        else:
            msg = 'حدث خطأ غير متوقع، يرجى المحاولة مجدداً'

        return JsonResponse({'status': 'error', 'message': msg})


# ============================================================
# استرجاع كلمة المرور
# ============================================================

@csrf_protect
@require_http_methods(['GET', 'POST'])
def forgot_password_view(request):
    if request.method == 'POST':
        step  = request.POST.get('step', '').strip()
        email = request.POST.get('email', '').strip()
        ip    = get_client_ip(request)

        if step == 'send_otp':
            if not email or '@' not in email:
                return JsonResponse({'status': 'error', 'message': 'بريد إلكتروني غير صالح'})
            if re.search(r"[<>\"';]", email):
                return JsonResponse({'status': 'error', 'message': 'مدخل غير صالح'}, status=400)
            try:
                user             = CustomUser.objects.get(email=email)
                success, err_msg = send_otp_email(user)
                if not success:
                    return JsonResponse({'status': 'error', 'message': err_msg})
                log_activity(user, 'OTP', description='طلب OTP',
                             ip=ip, request=request)
            except CustomUser.DoesNotExist:
                pass
            return JsonResponse({
                'status':  'success',
                'message': 'إذا كان البريد مسجلاً ستصلك رسالة خلال دقيقة'
            })

        if step == 'verify_otp':
            code = request.POST.get('code', '').strip()
            if not code or not code.isdigit() or len(code) != 6:
                return JsonResponse({'status': 'error', 'message': 'الرمز يجب أن يكون 6 أرقام'})
            try:
                user = CustomUser.objects.get(email=email)
                otp  = OTPVerification.objects.filter(
                    user=user, code=code, is_used=False
                ).latest('created_at')
                if not otp.is_valid():
                    return JsonResponse({'status': 'error', 'message': 'الرمز منتهي الصلاحية'})
                otp.is_used = True
                otp.save()
                request.session['reset_user_id']     = str(user.pk)
                request.session['reset_verified_at'] = str(timezone.now())
                return JsonResponse({'status': 'success'})
            except (CustomUser.DoesNotExist, OTPVerification.DoesNotExist):
                return JsonResponse({'status': 'error', 'message': 'الرمز غير صحيح'})

        if step == 'reset_password':
            user_id   = request.session.get('reset_user_id')
            password  = request.POST.get('password',  '').strip()
            password2 = request.POST.get('password2', '').strip()
            if not user_id:
                return JsonResponse({'status': 'error', 'message': 'انتهت الجلسة'})
            errors = {}
            if not password:
                errors['password'] = 'كلمة المرور مطلوبة'
            elif len(password) < 8:
                errors['password'] = '8 أحرف على الأقل'
            elif not any(c.isdigit() for c in password):
                errors['password'] = 'يجب أن تحتوي على رقم'
            if password and password2 and password != password2:
                errors['password2'] = 'كلمتا المرور غير متطابقتان'
            if errors:
                return JsonResponse({'status': 'error', 'errors': errors})
            try:
                user = CustomUser.objects.get(pk=user_id)
                user.set_password(password)
                user.save()
                request.session.pop('reset_user_id',     None)
                request.session.pop('reset_verified_at', None)
                log_activity(user, 'UPDATE',
                             description='تغيير كلمة المرور',
                             ip=ip, request=request)
                return JsonResponse({'status': 'success',
                                     'message': 'تم تغيير كلمة المرور ✅'})
            except CustomUser.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'حدث خطأ'})

    return render(request, 'main/forgot_password.html')


# ============================================================
# تسجيل الدخول — أدمن
# ============================================================

def admin_login_view(request):
    if request.user.is_authenticated and request.user.user_type == 'admin':
        return redirect('/admin-panel/dashboard/')

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':

        if request.POST.get('honeypot'):
            return JsonResponse({'status': 'error', 'message': 'غير مسموح'})

        identifier = request.POST.get('identifier', '').strip()
        password   = request.POST.get('password',   '').strip()

        if not identifier or not password:
            return JsonResponse({'status': 'error', 'message': 'يرجى ملء جميع الحقول'})

        ip          = get_client_ip(request)
        lockout_key = f'admin_lockout_{ip}'
        attempt_key = f'admin_attempts_{ip}'

        if cache.get(lockout_key):
            return JsonResponse({
                'status':    'locked',
                'message':   'تم تجميد الدخول 2 دقيقة',
                'remaining': 120,
            }, status=429)

        user = None
        try:
            u    = CustomUser.objects.get(username=identifier, user_type='admin')
            user = authenticate(request, username=u.username, password=password)
        except CustomUser.DoesNotExist:
            try:
                u    = CustomUser.objects.get(email=identifier, user_type='admin')
                user = authenticate(request, username=u.username, password=password)
            except CustomUser.DoesNotExist:
                pass

        if user is None or user.user_type != 'admin':
            attempts = cache.get(attempt_key, 0) + 1
            cache.set(attempt_key, attempts, 120)

            if attempts >= 5:
                cache.set(lockout_key, True, 120)
                cache.delete(attempt_key)
                return JsonResponse({
                    'status':    'locked',
                    'message':   'تم تجميد الدخول 2 دقيقة',
                    'remaining': 120,
                }, status=429)

            return JsonResponse({
                'status':        'error',
                'message':       'اسم المستخدم أو كلمة المرور غير صحيحة',
                'attempts_left': 5 - attempts,
                'errors':        {'identifier': 'بيانات الدخول غير صحيحة'},
            })

        if not user.is_active:
            return JsonResponse({'status': 'error', 'message': 'الحساب غير مفعّل'})

        if not user.is_approved:
            return JsonResponse({'status': 'error', 'message': 'الحساب قيد المراجعة'})

        login(request, user)
        cache.delete(attempt_key)

        user.login_count   = (user.login_count or 0) + 1
        user.last_login_ip = ip
        user.save(update_fields=['login_count', 'last_login_ip', 'last_login'])

        log_activity(user, 'LOGIN', description='دخول أدمن ناجح', request=request)

        return JsonResponse({
            'status':   'success',
            'message':  f'أهلاً {user.first_name} 👋',
            'redirect': '/admin-panel/dashboard/',
        })

    return render(request, 'main/admin_login.html')


# ============================================================
# API — دول / أسعار صرف / تحقق التفرد
# ============================================================

def countries_api(request):
    try:
        file_path = Path(settings.BASE_DIR) / 'static' / 'js' / 'countries.json'
        with open(file_path, 'r', encoding='utf-8') as f:
            countries = json.load(f)
        return JsonResponse({'countries': countries})
    except Exception as e:
        return JsonResponse({'countries': [], 'error': str(e)})


def exchange_rates_api(request):
    return JsonResponse(get_exchange_rates())


def faq_view(request):
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'created_at')
    return render(request, 'main/faq.html', {'faqs': faqs})


@csrf_protect
@require_POST
def check_unique_api(request):
    """
    API للتحقق من تفرد الحقول في الوقت الفعلي.
    Rate Limiting: 60 طلب / دقيقة لكل IP.
    """
    ip       = get_client_ip(request)
    rate_key = f'unique_api_{ip}'
    count    = cache.get(rate_key, 0)
    if count >= 60:
        return JsonResponse(
            {'unique': True, 'message': 'تجاوزت الحد المسموح، حاول لاحقاً'},
            status=429
        )
    cache.set(rate_key, count + 1, timeout=60)

    field = request.POST.get('field', '').strip()
    value = request.POST.get('value', '').strip()

    if not field or not value:
        return JsonResponse({'unique': True})

    # تنظيف المدخل من XSS
    if re.search(r'[<>\'";\\/\*]', value):
        return JsonResponse({'unique': True, 'message': 'مدخل غير صالح'})

    result = {'unique': True, 'message': ''}

    if field == 'username':
        if CustomUser.objects.filter(username=value).exists():
            result = {'unique': False, 'message': 'اسم المستخدم مستخدم مسبقاً'}

    elif field == 'email':
        if CustomUser.objects.filter(email=value.lower()).exists():
            result = {'unique': False, 'message': 'البريد الإلكتروني مستخدم مسبقاً'}

    elif field == 'id_number':
        if _id_exists_anywhere(value):
            result = {'unique': False, 'message': 'رقم الهوية مسجّل مسبقاً في النظام'}

    elif field == 'whatsapp':
        if _whatsapp_exists_anywhere(value):
            result = {'unique': False, 'message': 'رقم الواتساب مستخدم مسبقاً'}

    elif field == 'phone1':
        if _phone_exists_anywhere(value):
            result = {'unique': False, 'message': 'رقم الجوال مستخدم مسبقاً في النظام'}

    elif field == 'phone2':
        phone1_val = request.POST.get('phone1_value', '').strip()
        if phone1_val and value == phone1_val:
            result = {'unique': False, 'message': 'رقم الجوال الثاني مطابق للأول'}
        elif _phone_exists_anywhere(value):
            result = {'unique': False, 'message': 'رقم الجوال الثاني مستخدم مسبقاً في النظام'}

    return JsonResponse(result)


# ============================================================
# Helpers — إعادة التوجيه
# ============================================================

def _redirect_by_type(user, url_only=False):
    urls = {
        'admin':   '/admin-panel/dashboard/',
        'sponsor': '/sponsor/dashboard/',
    }
    url = urls.get(user.user_type, '/beneficiary/dashboard/')
    return url if url_only else redirect(url)


def _get_dashboard_url(user):
    return {
        'admin':   '/admin-panel/dashboard/',
        'sponsor': '/sponsor/dashboard/',
        'orphan':  '/beneficiary/dashboard/',
        'family':  '/beneficiary/dashboard/',
        'special': '/beneficiary/dashboard/',
    }.get(user.user_type, '/login/')


# ============================================================
# Helpers — تحقق التفرد (داخلي)
# ============================================================

def _id_exists_anywhere(id_number):
    """تحقق من عدم تكرار رقم الهوية في كل النظام"""
    return (
        CustomUser.objects.filter(id_number=id_number).exists()       or
        OrphanForm.objects.filter(id_number=id_number).exists()        or
        OrphanMother.objects.filter(id_number=id_number).exists()      or
        OrphanFather.objects.filter(id_number=id_number).exists()      or
        CurrentGuardian.objects.filter(id_number=id_number).exists()   or
        SpecialNeedsForm.objects.filter(id_number=id_number).exists()  or
        FamilyForm.objects.filter(id_number=id_number).exists()        or
        FamilyWife.objects.filter(id_number=id_number).exists()        or
        FamilyMember.objects.filter(id_number=id_number).exists()
    )


def _phone_exists_anywhere(phone):
    """تحقق من عدم تكرار رقم الجوال في كل النظام"""
    return (
        CustomUser.objects.filter(phone=phone).exists()                or
        OrphanForm.objects.filter(phone1=phone).exists()               or
        OrphanForm.objects.filter(phone2=phone).exists()               or
        SpecialNeedsForm.objects.filter(phone1=phone).exists()         or
        SpecialNeedsForm.objects.filter(phone2=phone).exists()         or
        FamilyForm.objects.filter(phone1=phone).exists()               or
        FamilyForm.objects.filter(phone2=phone).exists()
    )


def _whatsapp_exists_anywhere(whatsapp):
    """تحقق من عدم تكرار رقم الواتساب في عمود الواتساب فقط"""
    return (
        CustomUser.objects.filter(whatsapp=whatsapp).exists()          or
        OrphanForm.objects.filter(whatsapp=whatsapp).exists()          or
        SpecialNeedsForm.objects.filter(whatsapp=whatsapp).exists()    or
        FamilyForm.objects.filter(whatsapp=whatsapp).exists()
    )


# ============================================================
# Helpers — تحقق حقول الأنواع
# ============================================================
def _validate_orphan_fields(data, files, errors):
    """تحقق من الحقول الخاصة بالتسجيل كيتيم"""

    # بيانات اليتيم
    if not data.get('orphan_type', '').strip():
        errors['orphan_type'] = 'يرجى تحديد من فقد من الوالدين'
    if not data.get('birth_date', '').strip():
        errors['birth_date'] = 'تاريخ الميلاد مطلوب'
    if not data.get('health_status', '').strip():
        errors['health_status'] = 'الحالة الصحية مطلوبة'
    if not data.get('education_level', '').strip():
        errors['education_level'] = 'المستوى التعليمي مطلوب'
    if not data.get('school_name', '').strip():
        errors['school_name'] = 'اسم المدرسة مطلوب'

    # العنوان الحالي
    if not data.get('current_city', '').strip():
        errors['current_city'] = 'المدينة الحالية مطلوبة'
    if not data.get('current_street', '').strip():
        errors['current_street'] = 'الشارع الحالي مطلوب'
    if not data.get('current_landmark', '').strip():
        errors['current_landmark'] = 'أقرب معلم/مسجد مطلوب'

    # العنوان السابق
    if not data.get('previous_city', '').strip():
        errors['previous_city'] = 'المدينة السابقة مطلوبة'
    if not data.get('previous_street', '').strip():
        errors['previous_street'] = 'الشارع السابق مطلوب'
    if not data.get('previous_landmark', '').strip():
        errors['previous_landmark'] = 'أقرب معلم سابق مطلوب'

    # السكن
    if not data.get('housing_type', '').strip():
        errors['housing_type'] = 'نوع السكن مطلوب'
    if not data.get('housing_ownership', '').strip():
        errors['housing_ownership'] = 'ملكية السكن مطلوبة'

    # القصة
    if not data.get('story', '').strip():
        errors['story'] = 'قصة اليتيم مطلوبة'

    # بيانات الأم
    mother_id = data.get('mother_id_number', '').strip()
    if not mother_id:
        errors['mother_id_number'] = 'رقم هوية الأم مطلوب'
    else:
        try:
            validate_id_number(mother_id)
        except Exception as e:
            errors['mother_id_number'] = str(e)
        else:
            if _id_exists_anywhere(mother_id):
                errors['mother_id_number'] = 'رقم هوية الأم مسجّل مسبقاً'
    if not data.get('mother_first_name', '').strip():
        errors['mother_first_name'] = 'اسم الأم مطلوب'

    # بيانات الأب
    father_id = data.get('father_id_number', '').strip()
    if not father_id:
        errors['father_id_number'] = 'رقم هوية الأب مطلوب'
    else:
        try:
            validate_id_number(father_id)
        except Exception as e:
            errors['father_id_number'] = str(e)
        else:
            if _id_exists_anywhere(father_id):
                errors['father_id_number'] = 'رقم هوية الأب مسجّل مسبقاً'
    if not data.get('father_first_name', '').strip():
        errors['father_first_name'] = 'اسم الأب مطلوب'

    # المعيل الحالي
    guardian_id = data.get('guardian_id_number', '').strip()
    if not guardian_id:
        errors['guardian_id_number'] = 'رقم هوية المعيل مطلوب'
    else:
        try:
            validate_id_number(guardian_id)
        except Exception as e:
            errors['guardian_id_number'] = str(e)
        else:
            if _id_exists_anywhere(guardian_id):
                errors['guardian_id_number'] = 'رقم هوية المعيل مسجّل مسبقاً'
    for f, l in [
        ('guardian_first_name',    'اسم المعيل'),
        ('guardian_gender',        'جنس المعيل'),
        ('guardian_relation',      'صلة القرابة'),
        ('guardian_job',           'مهنة المعيل'),
        ('guardian_health_status', 'الحالة الصحية للمعيل'),
        ('guardian_education_level','المستوى التعليمي للمعيل'),
        ('guardian_monthly_income','الدخل الشهري للمعيل'),
        ('guardian_dependents',    'عدد من يعيلهم'),
    ]:
        if not data.get(f, '').strip():
            errors[f] = f'{l} مطلوب'

    # المستندات الإلزامية — بالـ prefix or_
    orphan_doc_map = {
        'هوية_الوصي':        'or_هوية_الوصي',
        'شهادة_ميلاد_الطفل': 'or_شهادة_ميلاد_الطفل',
        'شهادة_وفاة_الاب':   'or_شهادة_وفاة_الاب',
        'حجة_وصاية':         'or_حجة_وصاية',
    }
    for doc, form_key in orphan_doc_map.items():
        if f'doc_{form_key}' not in files:
            errors[f'doc_{form_key}'] = f'مستند {doc} مطلوب'
        else:
            try:
                validate_upload_file(files[f'doc_{form_key}'])
            except Exception as e:
                errors[f'doc_{form_key}'] = str(e)


def _validate_special_fields(data, files, errors):
    """تحقق من الحقول الخاصة بالتسجيل كذوي احتياجات"""

    if not data.get('birth_date', '').strip():
        errors['birth_date'] = 'تاريخ الميلاد مطلوب'
    if not data.get('health_status', '').strip():
        errors['health_status'] = 'الحالة الصحية مطلوبة'
    if not data.get('education_level', '').strip():
        errors['education_level'] = 'المستوى التعليمي مطلوب'

    # العنوان الحالي
    if not data.get('current_city', '').strip():
        errors['current_city'] = 'المدينة الحالية مطلوبة'
    if not data.get('current_street', '').strip():
        errors['current_street'] = 'الشارع الحالي مطلوب'
    if not data.get('current_landmark', '').strip():
        errors['current_landmark'] = 'أقرب معلم/مسجد مطلوب'

    # السكن
    if not data.get('housing_type', '').strip():
        errors['housing_type'] = 'نوع السكن مطلوب'
    if not data.get('housing_ownership', '').strip():
        errors['housing_ownership'] = 'ملكية السكن مطلوبة'

    # تفاصيل الحالة
    if not data.get('case_details', '').strip():
        errors['case_details'] = 'تفاصيل الحالة مطلوبة'

    # المعيل الحالي
    guardian_id = data.get('special_guardian_id_number', '').strip()
    if not guardian_id:
        errors['special_guardian_id_number'] = 'رقم هوية المعيل مطلوب'
    else:
        try:
            validate_id_number(guardian_id)
        except Exception as e:
            errors['special_guardian_id_number'] = str(e)
        else:
            if _id_exists_anywhere(guardian_id):
                errors['special_guardian_id_number'] = 'رقم هوية المعيل مسجّل مسبقاً'
    for f, l in [
        ('special_guardian_first_name',     'اسم المعيل'),
        ('special_guardian_gender',         'جنس المعيل'),
        ('special_guardian_relation',       'صلة القرابة'),
        ('special_guardian_job',            'مهنة المعيل'),
        ('special_guardian_health_status',  'الحالة الصحية للمعيل'),
        ('special_guardian_education_level','المستوى التعليمي للمعيل'),
        ('special_guardian_monthly_income', 'الدخل الشهري للمعيل'),
        ('special_guardian_dependents',     'عدد من يعيلهم'),
    ]:
        if not data.get(f, '').strip():
            errors[f] = f'{l} مطلوب'

    # المستندات الإلزامية — بالـ prefix sp_
    special_doc_map = {
        'هوية_المعيل':        'sp_هوية_المعيل',
        'هوية_الاب':          'sp_هوية_الاب',
        'هوية_الام':          'sp_هوية_الام',
        'شهادة_ميلاد_الشخص': 'sp_شهادة_ميلاد_الشخص',
        'التقرير_الطبي':      'sp_التقرير_الطبي',
        'هوية_المريض':        'sp_هوية_المريض',
    }
    for doc, form_key in special_doc_map.items():
        if f'doc_{form_key}' not in files:
            errors[f'doc_{form_key}'] = f'مستند {doc} مطلوب'
        else:
            try:
                validate_upload_file(files[f'doc_{form_key}'])
            except Exception as e:
                errors[f'doc_{form_key}'] = str(e)


def _validate_family_fields(data, files, errors):
    """تحقق من الحقول الخاصة بالتسجيل كأسرة"""

    # بيانات رب الأسرة
    for f, l in [
        ('family_first_name',      'الاسم الأول'),
        ('family_father_name_h',   'اسم الأب'),
        ('family_grand_name_h',    'اسم الجد'),
        ('family_family_name_h',   'اسم العائلة'),
        ('family_birth_date',      'تاريخ الميلاد'),
        ('family_gender',          'الجنس'),
        ('family_marital_status',  'الحالة الاجتماعية'),
        ('family_health_status',   'الحالة الصحية'),
        ('family_education_level', 'المستوى التعليمي'),
        ('family_job',             'المهنة'),
        ('family_members_count',   'عدد أفراد الأسرة'),
        ('family_sick_count',      'عدد المرضى'),
    ]:
        if not data.get(f, '').strip():
            errors[f] = f'{l} مطلوب'

    family_id = data.get('family_id_number', '').strip()
    if not family_id:
        errors['family_id_number'] = 'رقم الهوية مطلوب'
    else:
        try:
            validate_id_number(family_id)
        except Exception as e:
            errors['family_id_number'] = str(e)
        else:
            if _id_exists_anywhere(family_id):
                errors['family_id_number'] = 'رقم الهوية مسجّل مسبقاً'

    # العنوان الحالي
    if not data.get('family_current_city', '').strip():
        errors['family_current_city'] = 'المدينة الحالية مطلوبة'
    if not data.get('family_current_street', '').strip():
        errors['family_current_street'] = 'الشارع الحالي مطلوب'
    if not data.get('family_current_landmark', '').strip():
        errors['family_current_landmark'] = 'أقرب معلم/مسجد مطلوب'

    # السكن
    if not data.get('housing_type', '').strip():
        errors['housing_type'] = 'نوع السكن مطلوب'
    if not data.get('housing_ownership', '').strip():
        errors['housing_ownership'] = 'ملكية السكن مطلوبة'

    # الوضع العام
    if not data.get('family_general_status', '').strip():
        errors['family_general_status'] = 'الوضع العام للأسرة مطلوب'

    # الزوجة (إذا متزوج)
    if data.get('family_marital_status', '').strip() == 'متزوج':
        wife_id = data.get('wife_id_number', '').strip()
        if not wife_id:
            errors['wife_id_number'] = 'رقم هوية الزوجة مطلوب'
        else:
            try:
                validate_id_number(wife_id)
            except Exception as e:
                errors['wife_id_number'] = str(e)
            else:
                if _id_exists_anywhere(wife_id):
                    errors['wife_id_number'] = 'رقم هوية الزوجة مسجّل مسبقاً'
        for f, l in [
            ('wife_first_name',      'اسم الزوجة'),
            ('wife_birth_date',      'تاريخ ميلاد الزوجة'),
            ('wife_health_status',   'الحالة الصحية للزوجة'),
            ('wife_education_level', 'المستوى التعليمي للزوجة'),
        ]:
            if not data.get(f, '').strip():
                errors[f] = f'{l} مطلوب'

    # المعيل الحالي
    guardian_id = data.get('family_guardian_id_number', '').strip()
    if not guardian_id:
        errors['family_guardian_id_number'] = 'رقم هوية المعيل مطلوب'
    else:
        try:
            validate_id_number(guardian_id)
        except Exception as e:
            errors['family_guardian_id_number'] = str(e)
        else:
            if _id_exists_anywhere(guardian_id):
                errors['family_guardian_id_number'] = 'رقم هوية المعيل مسجّل مسبقاً'
    for f, l in [
        ('family_guardian_first_name',     'اسم المعيل'),
        ('family_guardian_gender',         'جنس المعيل'),
        ('family_guardian_relation',       'صلة القرابة'),
        ('family_guardian_job',            'مهنة المعيل'),
        ('family_guardian_health_status',  'الحالة الصحية للمعيل'),
        ('family_guardian_education_level','المستوى التعليمي للمعيل'),
        ('family_guardian_monthly_income', 'الدخل الشهري للمعيل'),
        ('family_guardian_dependents',     'عدد من يعيلهم'),
    ]:
        if not data.get(f, '').strip():
            errors[f] = f'{l} مطلوب'

    # المستندات الإلزامية — بالـ prefix fm_
    family_doc_map = {
        'هوية_الام':   'fm_هوية_الام',
        'هوية_الاب':   'fm_هوية_الاب',
        'هوية_المعيل': 'fm_هوية_المعيل',
    }
    for doc, form_key in family_doc_map.items():
        if f'doc_{form_key}' not in files:
            errors[f'doc_{form_key}'] = f'مستند {doc} مطلوب'
        else:
            try:
                validate_upload_file(files[f'doc_{form_key}'])
            except Exception as e:
                errors[f'doc_{form_key}'] = str(e)

# ============================================================
# Helpers — حفظ البيانات
# ============================================================
def _register_sponsor(user, data, files):
    """حفظ بيانات الكافل"""
    profile = SponsorProfile.objects.create(
        user    = user,
        job     = data.get('job',     ''),
        country = data.get('country', ''),
        city    = data.get('city',    ''),
    )
    if 'photo' in files:
        img = files['photo']
        if img.size <= 4 * 1024 * 1024:
            compressed = compress_image(img)
            profile.photo.save(img.name, compressed, save=True)
    return 'كافل'


def _register_orphan(user, data, files):
    """حفظ بيانات اليتيم"""
    form = OrphanForm(
        user             = user,
        first_name       = data.get('first_name',       ''),
        father_name      = data.get('father_name',      ''),
        grand_name       = data.get('grand_name',       ''),
        family_name      = data.get('family_name',      ''),
        birth_date       = data.get('birth_date',       '2000-01-01'),
        id_number        = data.get('id_number',        ''),
        nationality      = data.get('nationality',      'فلسطينية'),
        nationality_code = data.get('nationality_code', 'PS'),
        gender           = data.get('gender',           'ذكر'),
        orphan_type      = data.get('orphan_type',      'يتيم الأب'),
        health_status    = data.get('health_status',    'سليم'),
        education_level  = data.get('education_level',  'غير متعلم'),
        school_grade     = data.get('school_grade',     '') or None,
        school_name      = data.get('school_name',      ''),
        current_city     = data.get('current_city',     'غير محدد'),
        current_street   = data.get('current_street',   ''),
        current_landmark = data.get('current_landmark', ''),
        previous_city    = data.get('previous_city',    '') or '',
        previous_street  = data.get('previous_street',  '') or '',
        previous_landmark= data.get('previous_landmark','') or '',
        phone1           = data.get('phone1',           ''),
        phone1_country   = data.get('phone1_country',   '+970'),
        phone2           = data.get('phone2',           '') or '',
        phone2_country   = data.get('phone2_country',   '+970'),
        whatsapp         = data.get('whatsapp',         ''),
        whatsapp_country = data.get('whatsapp_country', '+970'),
        housing_type     = data.get('housing_type',     'خيمة'),
        housing_ownership= data.get('housing_ownership','ملك'),
        monthly_rent     = data.get('monthly_rent',     '') or None,
        story            = data.get('story',            ''),
    )
    if 'photo' in files:
        compressed = compress_image(files['photo'])
        form.photo.save(files['photo'].name, compressed, save=False)
    form.save()

    # بيانات الأم
    if data.get('mother_id_number'):
        OrphanMother.objects.create(
            form             = form,
            first_name       = data.get('mother_first_name',      ''),
            father_name      = data.get('mother_father_name',      ''),
            grand_name       = data.get('mother_grand_name',       ''),
            family_name      = data.get('mother_family_name',      ''),
            birth_date       = data.get('mother_birth_date',       '2000-01-01'),
            id_number        = data.get('mother_id_number',        ''),
            nationality      = data.get('mother_nationality',      'فلسطينية'),
            nationality_code = data.get('mother_nationality_code', 'PS'),
            gender           = 'أنثى',
            is_alive         = data.get('mother_is_alive', 'true') == 'true',
            death_date       = data.get('mother_death_date',   '') or None,
            death_reason     = data.get('mother_death_reason', '') or '',
            health_status    = data.get('mother_health_status',    'سليم'),
            education_level  = data.get('mother_education_level',  'غير متعلم'),
            job              = data.get('mother_job',              'ربة بيت'),
            monthly_income   = data.get('mother_monthly_income',   0) or 0,
        )

    # بيانات الأب
    if data.get('father_id_number'):
        OrphanFather.objects.create(
            form             = form,
            first_name       = data.get('father_first_name',      ''),
            father_name      = data.get('father_father_name',      ''),
            grand_name       = data.get('father_grand_name',       ''),
            family_name      = data.get('father_family_name',      ''),
            birth_date       = data.get('father_birth_date',       '2000-01-01'),
            id_number        = data.get('father_id_number',        ''),
            nationality      = data.get('father_nationality',      'فلسطينية'),
            nationality_code = data.get('father_nationality_code', 'PS'),
            gender           = 'ذكر',
            is_alive         = data.get('father_is_alive', 'false') == 'true',
            death_date       = data.get('father_death_date',   '') or None,
            death_reason     = data.get('father_death_reason', '') or '',
            health_status    = data.get('father_health_status',    'سليم'),
            education_level  = data.get('father_education_level',  'غير متعلم'),
            job              = data.get('father_job',              'أخرى'),
            children_count   = data.get('father_children_count',   0) or 0,
            income_before    = data.get('father_income_before',    '') or None,
            pension_after    = data.get('father_pension_after',    '') or None,
        )

    _save_guardian(data, 'orphan', form.id, prefix='guardian')
    _save_family_members(data, 'orphan', form.id)
    _save_documents(form, files, OrphanDocument, prefix='or_')
    return 'يتيم'


def _register_special(user, data, files):
    """حفظ بيانات ذوي الاحتياجات"""
    form = SpecialNeedsForm(
        user             = user,
        first_name       = data.get('first_name',       ''),
        father_name      = data.get('father_name',      ''),
        grand_name       = data.get('grand_name',       ''),
        family_name      = data.get('family_name',      ''),
        birth_date       = data.get('birth_date',       '2000-01-01'),
        id_number        = data.get('id_number',        ''),
        nationality      = data.get('nationality',      'فلسطينية'),
        nationality_code = data.get('nationality_code', 'PS'),
        gender           = data.get('gender',           'ذكر'),
        health_status    = data.get('health_status',    'سليم'),
        education_level  = data.get('education_level',  'غير متعلم'),
        school_grade     = data.get('school_grade',     '') or None,
        school_name      = data.get('school_name',      ''),
        current_city     = data.get('current_city',     'غير محدد'),
        current_street   = data.get('current_street',   ''),
        current_landmark = data.get('current_landmark', ''),
        previous_city    = data.get('previous_city',    '') or '',
        previous_street  = data.get('previous_street',  '') or '',
        previous_landmark= data.get('previous_landmark','') or '',
        phone1           = data.get('phone1',           ''),
        phone1_country   = data.get('phone1_country',   '+970'),
        phone2           = data.get('phone2',           '') or '',
        phone2_country   = data.get('phone2_country',   '+970'),
        whatsapp         = data.get('whatsapp',         ''),
        whatsapp_country = data.get('whatsapp_country', '+970'),
        housing_type     = data.get('housing_type',     'خيمة'),
        housing_ownership= data.get('housing_ownership','ملك'),
        monthly_rent     = data.get('monthly_rent',     '') or None,
        case_details     = data.get('case_details',     ''),
    )
    if 'photo' in files:
        compressed = compress_image(files['photo'])
        form.photo.save(files['photo'].name, compressed, save=False)
    form.save()

    _save_guardian(data, 'special', form.id, prefix='special_guardian')
    _save_family_members(data, 'special', form.id)
    _save_documents(form, files, SpecialDocument, prefix='sp_')
    return 'ذوو احتياجات خاصة'


def _register_family(user, data, files):
    """حفظ بيانات الأسرة"""
    form = FamilyForm(
        user              = user,
        first_name        = data.get('family_first_name',    ''),
        father_name       = data.get('family_father_name_h', ''),
        grand_name        = data.get('family_grand_name_h',  ''),
        family_name       = data.get('family_family_name_h', ''),
        birth_date        = data.get('family_birth_date',    '2000-01-01'),
        id_number         = data.get('family_id_number',     ''),
        nationality       = data.get('nationality',          'فلسطينية'),
        nationality_code  = data.get('nationality_code',     'PS'),
        gender            = data.get('family_gender',        'ذكر'),
        is_alive          = data.get('head_is_alive', 'true') == 'true',
        marital_status    = data.get('family_marital_status','متزوج'),
        health_status     = data.get('family_health_status', 'سليم'),
        education_level   = data.get('family_education_level','غير متعلم'),
        job               = data.get('family_job',           'أخرى'),
        current_city      = data.get('family_current_city',  'غير محدد'),
        current_street    = data.get('family_current_street',''),
        current_landmark  = data.get('family_current_landmark',''),
        previous_city     = data.get('family_previous_city', '') or '',
        previous_street   = data.get('family_previous_street','') or '',
        previous_landmark = data.get('family_previous_landmark','') or '',
        phone1            = data.get('phone1',               ''),
        phone1_country    = data.get('phone1_country',       '+970'),
        phone2            = data.get('phone2',               '') or '',
        phone2_country    = data.get('phone2_country',       '+970'),
        whatsapp          = data.get('whatsapp',             ''),
        whatsapp_country  = data.get('whatsapp_country',     '+970'),
        housing_type      = data.get('housing_type',         'خيمة'),
        housing_ownership = data.get('housing_ownership',    'ملك'),
        monthly_rent      = data.get('monthly_rent',         '') or None,
        family_members_count = data.get('family_members_count', 1) or 1,
        sick_members_count   = data.get('family_sick_count',    0) or 0,
        general_status    = data.get('family_general_status',''),
    )
    if 'family_photo' in files:
        compressed = compress_image(files['family_photo'])
        form.photo.save(files['family_photo'].name, compressed, save=False)
    elif 'photo' in files:
        compressed = compress_image(files['photo'])
        form.photo.save(files['photo'].name, compressed, save=False)
    form.save()

    # بيانات الزوجة (عند متزوج فقط)
    if data.get('family_marital_status') == 'متزوج' and data.get('wife_id_number'):
        wife = FamilyWife(
            form             = form,
            first_name       = data.get('wife_first_name',       ''),
            father_name      = data.get('wife_father_name',       ''),
            grand_name       = data.get('wife_grand_name',        ''),
            family_name      = data.get('wife_family_name',       ''),
            birth_date       = data.get('wife_birth_date',        '2000-01-01'),
            id_number        = data.get('wife_id_number',         ''),
            nationality      = data.get('wife_nationality',       'فلسطينية'),
            nationality_code = data.get('wife_nationality_code',  'PS'),
            gender           = 'أنثى',
            health_status    = data.get('wife_health_status',     'سليم'),
            education_level  = data.get('wife_education_level',   'غير متعلم'),
        )
        if 'wife_photo' in files:
            compressed = compress_image(files['wife_photo'])
            wife.photo.save(files['wife_photo'].name, compressed, save=False)
        wife.save()

    _save_guardian(data, 'family', form.id, prefix='family_guardian')
    _save_family_members(data, 'family', form.id)
    _save_documents(form, files, FamilyDocument, prefix='fm_')
    return 'أسرة'


def _save_guardian(data, form_type, form_id, prefix='guardian'):
    """حفظ المعيل الحالي — يعمل مع أي prefix"""
    id_number = data.get(f'{prefix}_id_number', '').strip()
    if not id_number:
        return
    CurrentGuardian.objects.create(
        form_type        = form_type,
        form_id          = form_id,
        first_name       = data.get(f'{prefix}_first_name',      ''),
        father_name      = data.get(f'{prefix}_father_name',      ''),
        grand_name       = data.get(f'{prefix}_grand_name',       ''),
        family_name      = data.get(f'{prefix}_family_name',      ''),
        birth_date       = data.get(f'{prefix}_birth_date',       '2000-01-01'),
        id_number        = id_number,
        nationality      = data.get(f'{prefix}_nationality',      'فلسطينية'),
        nationality_code = data.get(f'{prefix}_nationality_code', 'PS'),
        gender           = data.get(f'{prefix}_gender',           'ذكر'),
        health_status    = data.get(f'{prefix}_health_status',    'سليم'),
        education_level  = data.get(f'{prefix}_education_level',  'غير متعلم'),
        job              = data.get(f'{prefix}_job',              'أخرى'),
        monthly_income   = data.get(f'{prefix}_monthly_income',   0) or 0,
        relation         = data.get(f'{prefix}_relation',         'أخرى'),
        dependents       = data.get(f'{prefix}_dependents',       1) or 1,
    )


def _save_family_members(data, form_type, form_id):
    """حفظ أفراد الأسرة من JSON"""
    members_json = data.get('family_members_json', '[]')
    try:
        members = json.loads(members_json)
    except Exception:
        return
    for m in members:
        if not m.get('id_number'):
            continue
        FamilyMember.objects.create(
            form_type        = form_type,
            form_id          = form_id,
            first_name       = m.get('first_name',      ''),
            father_name      = m.get('father_name',      ''),
            grand_name       = m.get('grand_name',       ''),
            family_name      = m.get('family_name',      ''),
            birth_date       = m.get('birth_date',       '2000-01-01'),
            id_number        = m.get('id_number',        ''),
            nationality      = m.get('nationality',      'فلسطينية'),
            nationality_code = m.get('nationality_code', 'PS'),
            gender           = m.get('gender',           'ذكر'),
            health_status    = m.get('health_status',    'سليم'),
            education_level  = m.get('education_level',  'غير متعلم'),
            school_grade     = m.get('school_grade',     '') or None,
            marital_status   = m.get('marital_status',   'أعزب'),
            relation         = m.get('relation',         'أخرى'),
        )


def _save_documents(form_obj, files, doc_model, prefix=''):
    # جلب الاسم ورقم الهوية من النموذج
    full_name = form_obj.get_full_name() if hasattr(form_obj, 'get_full_name') else ''
    id_number = getattr(form_obj, 'id_number', '')

    for doc_type, _ in doc_model.DOC_TYPES:
        file_key = f'doc_{prefix}{doc_type}'
        for i, f in enumerate(files.getlist(file_key)):
            if f.size <= 4 * 1024 * 1024:
                # بناء اسم الملف
                ext = os.path.splitext(f.name)[1].lower()
                suffix = f'_{i + 1}' if i > 0 else ''
                new_name = f'{full_name}_{id_number}_{doc_type}{suffix}{ext}'
                # تنظيف الاسم من الرموز غير المسموحة
                new_name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', new_name)

                # إعادة تسمية الملف
                from django.core.files.base import ContentFile
                content = ContentFile(f.read())

                obj = doc_model(form=form_obj, doc_type=doc_type)
                obj.file.save(new_name, content, save=True)