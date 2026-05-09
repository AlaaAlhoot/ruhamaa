import re
import os
from django.core.exceptions import ValidationError


ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.pdf']
ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf']


def validate_id_number(value):
    if not re.match(r'^[9847]\d{8}$', str(value)):
        raise ValidationError('رقم الهوية يجب أن يكون 9 أرقام ويبدأ بـ 9 أو 8 أو 4 أو 7')


def validate_arabic_text(value):
    if not re.match(r'^[\u0600-\u06FF a-zA-Z\s]+$', str(value)):
        raise ValidationError('يجب إدخال نص عربي أو إنجليزي فقط')


def validate_image_size(image):
    if image.size > 4 * 1024 * 1024:
        raise ValidationError('حجم الصورة يجب أن لا يتجاوز 4 ميغابايت')


def validate_upload_file(file):
    """التحقق الشامل من الملفات المرفوعة"""
    # الحجم
    if file.size > 4 * 1024 * 1024:
        raise ValidationError('حجم الملف يجب أن لا يتجاوز 4 ميغابايت')

    # الامتداد
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError('يُسمح فقط بـ JPG أو PNG أو PDF')

    # اسم الملف — منع الأسماء الخطيرة
    if re.search(r'[<>:"/\\|?*\x00-\x1F]', file.name):
        raise ValidationError('اسم الملف يحتوي على رموز غير مسموح بها')

    # محتوى الملف الحقيقي
    try:
        import magic
        file.seek(0)
        mime = magic.from_buffer(file.read(2048), mime=True)
        file.seek(0)
        if mime not in ALLOWED_MIME_TYPES:
            raise ValidationError('محتوى الملف غير صالح أو مشبوه')
    except ImportError:
        pass  # إذا لم تكن مكتبة magic مثبّتة نتجاوزها


def validate_unique_fields(user_type, email, phone, id_number=None, username=None):
    """التحقق من عدم تكرار البيانات"""
    from core.models import CustomUser
    errors = {}

    if email and CustomUser.objects.filter(email=email).exists():
        errors['email'] = 'البريد الإلكتروني مستخدم مسبقاً'

    if phone and CustomUser.objects.filter(phone=phone).exists():
        errors['phone'] = 'رقم الجوال مستخدم مسبقاً'

    if id_number and CustomUser.objects.filter(id_number=id_number).exists():
        errors['id_number'] = 'رقم الهوية مستخدم مسبقاً'

    if username and CustomUser.objects.filter(username=username).exists():
        errors['username'] = 'اسم المستخدم مستخدم مسبقاً'

    return errors