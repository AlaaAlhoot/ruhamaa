import os
import re
import random
import string
import requests
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from PIL import Image
import io


# ==================== أسعار العملات ====================
def get_exchange_rates():
    from django.core.cache import cache
    cached = cache.get('exchange_rates')
    if cached:
        return cached

    # محاولة أولى — frankfurter (مجاني، بدون مفتاح، محدّث يومياً)
    try:
        res  = requests.get(
            'https://api.frankfurter.app/latest?from=USD&to=ILS,EUR',
            timeout=5
        )
        data = res.json()
        ils  = data.get('rates', {}).get('ILS', 0)
        eur  = data.get('rates', {}).get('EUR', 0)
        if ils > 0:
            rates = {
                'USD_TO_ILS': round(ils, 4),
                'ILS_TO_USD': round(1 / ils, 4),
                'USD_TO_EUR': round(eur, 4),
                'updated_at': data.get('date', ''),
                'source':     'frankfurter',
            }
            cache.set('exchange_rates', rates, timeout=1800)
            return rates
    except Exception:
        pass

    # محاولة ثانية — fawazahmed0 (مجاني، بدون حد يومي)
    try:
        res  = requests.get(
            'https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json',
            timeout=5
        )
        data = res.json()
        ils  = data.get('usd', {}).get('ils', 0)
        eur  = data.get('usd', {}).get('eur', 0)
        if ils > 0:
            rates = {
                'USD_TO_ILS': round(ils, 4),
                'ILS_TO_USD': round(1 / ils, 4),
                'USD_TO_EUR': round(eur, 4),
                'updated_at': data.get('date', ''),
                'source':     'fawazahmed0',
            }
            cache.set('exchange_rates', rates, timeout=1800)
            return rates
    except Exception:
        pass

    # محاولة ثالثة — open.er-api (الأصلي كـ fallback)
    try:
        res  = requests.get('https://open.er-api.com/v6/latest/USD', timeout=5)
        data = res.json()
        if data.get('result') == 'success':
            ils = data['rates'].get('ILS', 0)
            if ils > 0:
                rates = {
                    'USD_TO_ILS': round(ils, 4),
                    'ILS_TO_USD': round(1 / ils, 4),
                    'USD_TO_EUR': round(data['rates'].get('EUR', 0.92), 4),
                    'updated_at': data.get('time_last_update_utc', ''),
                    'source':     'open.er-api',
                }
                cache.set('exchange_rates', rates, timeout=1800)
                return rates
    except Exception:
        pass

    # fallback نهائي
    return {
        'USD_TO_ILS': 3.65,
        'ILS_TO_USD': 0.274,
        'USD_TO_EUR': 0.92,
        'updated_at': '',
        'source':     'fallback',
    }


def shekel_to_dollar(amount):
    return round(float(amount) * get_exchange_rates()['ILS_TO_USD'], 2)


def dollar_to_shekel(amount):
    return round(float(amount) * get_exchange_rates()['USD_TO_ILS'], 2)


# ==================== بيانات الدول ====================

def get_countries():
    """يجلب من الملف المحلي أولاً ثم من API"""
    from django.core.cache import cache
    cached = cache.get('countries_list')
    if cached:
        return cached

    # محاولة قراءة الملف المحلي
    local_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'countries_data.json')
    if os.path.exists(local_path):
        import json
        with open(local_path, encoding='utf-8') as f:
            countries = json.load(f)
        cache.set('countries_list', countries, timeout=7 * 24 * 3600)
        return countries

    # fallback
    return [
        {'code': 'PS', 'name': 'فلسطين',         'flag': '🇵🇸', 'dial': '+970'},
        {'code': 'EG', 'name': 'مصر',             'flag': '🇪🇬', 'dial': '+20'},
        {'code': 'JO', 'name': 'الأردن',           'flag': '🇯🇴', 'dial': '+962'},
        {'code': 'SA', 'name': 'السعودية',         'flag': '🇸🇦', 'dial': '+966'},
        {'code': 'AE', 'name': 'الإمارات',         'flag': '🇦🇪', 'dial': '+971'},
        {'code': 'TR', 'name': 'تركيا',            'flag': '🇹🇷', 'dial': '+90'},
        {'code': 'DE', 'name': 'ألمانيا',          'flag': '🇩🇪', 'dial': '+49'},
        {'code': 'US', 'name': 'الولايات المتحدة', 'flag': '🇺🇸', 'dial': '+1'},
        {'code': 'GB', 'name': 'المملكة المتحدة',  'flag': '🇬🇧', 'dial': '+44'},
    ]


# ==================== OTP ====================

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(user):
    from .models import OTPVerification, OTPAttempt

    today      = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())

    attempt, _ = OTPAttempt.objects.get_or_create(
        email=user.email, date=today,
        defaults={'week_start': week_start, 'attempts': 0, 'week_attempts': 0}
    )
    if attempt.week_start != week_start:
        attempt.week_start    = week_start
        attempt.week_attempts = 0
        attempt.save()

    if attempt.attempts >= 3:
        return False, 'تجاوزت الحد اليومي (3 محاولات). حاول غداً.'
    if attempt.week_attempts >= 15:
        return False, 'تجاوزت الحد الأسبوعي (15 محاولة). حاول الأسبوع القادم.'

    OTPVerification.objects.filter(user=user, is_used=False).update(is_used=True)

    code       = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=10)
    otp        = OTPVerification.objects.create(user=user, code=code, expires_at=expires_at)

    try:
        send_mail(
            subject='رمز التحقق — منصة رُحَمَاء',
            message=(
                f'السلام عليكم {user.get_full_name()},\n\n'
                f'رمز التحقق: {code}\n\n'
                f'صالح 10 دقائق فقط ولمرة واحدة.\n\n'
                f'فريق منصة رُحَمَاء'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        attempt.attempts      += 1
        attempt.week_attempts += 1
        attempt.save()
        return True, ''
    except Exception as e:
        otp.delete()
        return False, f'فشل الإرسال: {str(e)}'


# ==================== البريد العام ====================

def send_email(to, subject, message):
    try:
        send_mail(subject, message,
                  settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
        return True
    except Exception:
        return False


def send_approval_email(user):
    return send_email(
        user.email,
        'تم قبول حسابك ✅ — منصة رُحَمَاء',
        f'السلام عليكم {user.get_full_name()},\n\n'
        f'تمت الموافقة على حسابك في منصة رُحَمَاء.\n'
        f'يمكنك الآن تسجيل الدخول.\n\n'
        f'فريق منصة رُحَمَاء'
    )


def send_rejection_email(user, complaint_url=''):
    return send_email(
        user.email,
        'اعتذار — منصة رُحَمَاء',
        f'السلام عليكم {user.get_full_name()},\n\n'
        f'نعتذر، تم رفض طلب انضمامك.\n'
        f'للاستفسار تواصل معنا عبر: {complaint_url}\n\n'
        f'فريق منصة رُحَمَاء'
    )


def send_receipt_approved_email(user, amount_shekel, amount_dollar):
    return send_email(
        user.email,
        'تم قبول الوصل المالي ✅ — منصة رُحَمَاء',
        f'السلام عليكم {user.get_full_name()},\n\n'
        f'تم قبول الوصل: {amount_shekel}₪ / ${amount_dollar}\n'
        f'تم رصده في حسابك.\n\n'
        f'فريق منصة رُحَمَاء'
    )


def send_receipt_rejected_email(user, reason):
    return send_email(
        user.email,
        'تم رفض الوصل المالي — منصة رُحَمَاء',
        f'السلام عليكم {user.get_full_name()},\n\n'
        f'تم رفض الوصل المالي.\nالسبب: {reason}\n\n'
        f'فريق منصة رُحَمَاء'
    )


# ==================== الصور ====================

def compress_image(image_field, quality=75, max_width=800):
    img = Image.open(image_field)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    if img.width > max_width:
        ratio  = max_width / img.width
        img    = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=quality, optimize=True)
    output.seek(0)
    return output


# ==================== IP ====================

def get_client_ip(request):
    x = request.META.get('HTTP_X_FORWARDED_FOR')
    return x.split(',')[0].strip() if x else request.META.get('REMOTE_ADDR')


# ==================== سجل النشاط ====================

def log_activity(user, action, description='', target_model=None,
                 target_id=None, old_value=None, new_value=None,
                 ip=None, request=None):
    from .models import ActivityLog
    if request and not ip:
        ip = get_client_ip(request)
    ActivityLog.objects.create(
        user         = user,
        action       = action,
        description  = description,
        target_model = target_model,
        target_id    = str(target_id) if target_id else None,
        old_value    = old_value,
        new_value    = new_value,
        ip_address   = ip,
        user_agent   = request.META.get('HTTP_USER_AGENT', '') if request else '',
    )


# ==================== الإشعارات ====================

def create_notification(recipient, ntype, title, message,
                        sender=None, action_url=None):
    from .models import Notification
    Notification.objects.create(
        recipient=recipient, sender=sender,
        ntype=ntype, title=title,
        message=message, action_url=action_url,
    )


def notify_admins(ntype, title, message, sender=None, action_url=None):
    from .models import CustomUser
    for admin in CustomUser.objects.filter(user_type='admin', is_active=True):
        create_notification(admin, ntype, title, message, sender, action_url)


# ==================== تسمية الملفات ====================

def build_safe_filename(full_name, id_number, doc_type, original_name):
    ext        = os.path.splitext(original_name)[1].lower()
    clean_name = full_name.replace(' ', '_')
    clean_type = doc_type.replace(' ', '_')
    filename   = f"{clean_type}_{clean_name}_{id_number}{ext}"
    return re.sub(r'[^\w\u0600-\u06FF._-]', '', filename)

# ==================== رقم التسجيل ====================
def generate_reg_number(user):
    from .models import CustomUser

    TYPE_MAP = {
        'orphan':  'يتيم',
        'family':  'أسرة',
        'special': 'ذوو_احتياجات',
        'sponsor': 'كافل',
    }
    label = TYPE_MAP.get(user.user_type, user.user_type)
    now   = timezone.now()
    ym    = now.strftime('%Y%m')

    total = CustomUser.objects.filter(
        user_type=user.user_type,
        is_approved=True,
        registration_number__isnull=False,
    ).count() + 1

    monthly = CustomUser.objects.filter(
        user_type=user.user_type,
        is_approved=True,
        registration_number__isnull=False,
        date_joined__year=now.year,
        date_joined__month=now.month,
    ).count() + 1

    return f'{label}-{total}-{ym}-{monthly}'


# ==================== الوقت ====================
def fmt_dt(dt):
    """تحويل datetime للتوقيت المحلي وتنسيقه"""
    from django.utils import timezone
    if not dt:
        return '—'
    return timezone.localtime(dt).strftime('%Y/%m/%d %H:%M')