from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import ForeignKey, TextField, DateTimeField, SET_NULL, CASCADE
from django.utils import timezone
import uuid


# ==================== Manager ====================

class CustomUserManager(BaseUserManager):

    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('البريد الإلكتروني مطلوب')
        email = self.normalize_email(email)
        user  = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff',    True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active',   True)
        extra_fields.setdefault('is_approved', True)
        extra_fields.setdefault('user_type',   'admin')
        return self.create_user(username, email, password, **extra_fields)


# ==================== CustomUser ====================
#core/models.py
class CustomUser(AbstractBaseUser, PermissionsMixin):

    USER_TYPES = [
        ('admin',   'مدير النظام'),
        ('sponsor', 'كافل'),
        ('orphan',  'يتيم'),
        ('family',  'أسرة'),
        ('special', 'ذوو احتياجات خاصة'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username         = models.CharField(max_length=150, unique=True, verbose_name='اسم المستخدم')
    email            = models.EmailField(unique=True, verbose_name='البريد الإلكتروني')
    user_type        = models.CharField(max_length=20, choices=USER_TYPES, verbose_name='نوع المستخدم')

    # الاسم الرباعي
    first_name       = models.CharField(max_length=50, verbose_name='الاسم الأول')
    father_name      = models.CharField(max_length=50, verbose_name='اسم الأب', default='')
    grand_name       = models.CharField(max_length=50, verbose_name='اسم الجد', default='')
    family_name      = models.CharField(max_length=50, verbose_name='اسم العائلة')

    # التعريف
    id_number        = models.CharField(max_length=9, unique=True, null=True, blank=True,
                                        verbose_name='رقم الهوية')
    registration_number = models.CharField(
        max_length=40, unique=True, null=True, blank=True,
        verbose_name='رقم التسجيل'
    )

    # الجوال — يُجلب كود الدولة من Phone Picker API
    phone_country    = models.CharField(max_length=10, default='+970',
                                        verbose_name='كود الدولة (الجوال)')
    phone            = models.CharField(max_length=20, verbose_name='رقم الجوال')

    # الواتساب — يُجلب كود الدولة من Phone Picker API
    whatsapp_country = models.CharField(max_length=10, default='+970',
                                        verbose_name='كود الدولة (واتساب)')
    whatsapp         = models.CharField(max_length=20, null=True, blank=True,
                                        verbose_name='رقم الواتساب')

    # الجنسية — يُجلب من RestCountries API
    nationality      = models.CharField(max_length=100, default='فلسطينية',
                                        verbose_name='الجنسية')
    nationality_code = models.CharField(max_length=5, default='PS',
                                        verbose_name='كود الجنسية')
    gender = models.CharField(
        max_length=10,
        choices=[('ذكر', 'ذكر'), ('أنثى', 'أنثى')],
        blank=True
    )

    # الصورة الشخصية
    profile_image    = models.ImageField(upload_to='profiles/', null=True, blank=True,
                                         verbose_name='الصورة الشخصية')

    # الحالة
    is_active        = models.BooleanField(default=True,  verbose_name='نشط')
    is_approved      = models.BooleanField(default=False, verbose_name='موافق عليه')
    is_staff         = models.BooleanField(default=False)
    can_access_settings = models.BooleanField(default=False, verbose_name='الوصول للإعدادات')
    can_manage_beneficiaries = models.BooleanField(default=False, verbose_name='إدارة المستفيدين')
    can_manage_sponsors = models.BooleanField(default=False, verbose_name='إدارة الكفلاء')
    can_manage_payments = models.BooleanField(default=False, verbose_name='إدارة الدفعات')
    can_manage_aids = models.BooleanField(default=False, verbose_name='إدارة المساعدات')
    can_view_logs = models.BooleanField(default=False, verbose_name='عرض السجلات')


    # الوضع الليلي محفوظ في DB
    dark_mode        = models.BooleanField(default=False, verbose_name='الوضع الليلي')
    allow_direct_comm = models.BooleanField(default=False, verbose_name='السماح بالتواصل المباشر')

    # إحصائيات الدخول
    login_count      = models.PositiveIntegerField(default=0, verbose_name='عدد مرات الدخول')
    last_login_ip    = models.GenericIPAddressField(null=True, blank=True,
                                                    verbose_name='آخر IP')
    last_seen        = models.DateTimeField(null=True, blank=True, verbose_name='آخر ظهور')

    date_joined      = models.DateTimeField(default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table            = 'core_users'
        verbose_name        = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def get_full_name(self):
        return f"{self.first_name} {self.father_name} {self.grand_name} {self.family_name}".strip()

    def get_short_name(self):
        return f"{self.first_name} {self.family_name}".strip()

    def get_full_phone(self):
        return f"{self.phone_country}{self.phone}"

    def get_full_whatsapp(self):
        if self.whatsapp:
            return f"{self.whatsapp_country}{self.whatsapp}"
        return ''

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_user_type_display()})"


# ==================== OTP ====================

class OTPVerification(models.Model):
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='otps')
    code       = models.CharField(max_length=6,   verbose_name='الرمز')
    is_used    = models.BooleanField(default=False, verbose_name='مستخدم')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name='ينتهي في')

    class Meta:
        db_table            = 'core_otp'
        verbose_name        = 'رمز OTP'
        verbose_name_plural = 'رموز OTP'

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"OTP — {self.user.username}"


# ==================== OTP Attempts ====================

class OTPAttempt(models.Model):
    email         = models.EmailField(verbose_name='البريد الإلكتروني')
    date          = models.DateField(auto_now_add=True)
    attempts      = models.PositiveIntegerField(default=0, verbose_name='المحاولات اليومية')
    week_start    = models.DateField(null=True, blank=True, verbose_name='بداية الأسبوع')
    week_attempts = models.PositiveIntegerField(default=0, verbose_name='المحاولات الأسبوعية')

    class Meta:
        db_table        = 'core_otp_attempts'
        unique_together = ['email', 'date']
        verbose_name    = 'محاولة OTP'

    def __str__(self):
        return f"{self.email} — {self.date} — {self.attempts}"


# ==================== الإشعارات ====================

class Notification(models.Model):

    TYPES = [
        ('NEW_USER',      'مستخدم جديد'),
        ('APPROVED',      'موافقة على الحساب'),
        ('REJECTED',      'رفض الحساب'),
        ('NEW_RECEIPT',   'وصل مالي جديد'),
        ('RECEIPT_OK',    'موافقة على الوصل'),
        ('RECEIPT_REJ',   'رفض الوصل'),
        ('NEW_MSG',       'رسالة جديدة'),
        ('COMM_ALLOWED',  'تفعيل تواصل مباشر'),
        ('PAYMENT_DUE',   'موعد دفعة قادم'),
        ('ANNOUNCEMENT',  'إعلان جديد'),
        ('SECURITY',      'تنبيه أمني'),
        ('SYSTEM',        'إشعار نظام'),
    ]

    recipient   = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                    related_name='notifications',
                                    verbose_name='المستلم')
    sender      = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='sent_notifications',
                                    verbose_name='المُرسِل')
    ntype       = models.CharField(max_length=20, choices=TYPES,
                                   default='SYSTEM', verbose_name='النوع')
    title       = models.CharField(max_length=200, verbose_name='العنوان')
    message     = models.TextField(verbose_name='الرسالة')
    is_read     = models.BooleanField(default=False, verbose_name='مقروء')
    action_url  = models.CharField(max_length=300, null=True, blank=True,
                                   verbose_name='رابط الإجراء')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'core_notifications'
        ordering            = ['-created_at']
        verbose_name        = 'إشعار'
        verbose_name_plural = 'الإشعارات'

    def __str__(self):
        return f"{self.title} → {self.recipient.get_short_name()}"
class SmartAlert(models.Model):

    LEVELS = [
        ('critical', '🔴 حرجة'),
        ('high',     '🟠 عالية'),
        ('medium',   '🟡 متوسطة'),
        ('info',     '🟢 معلوماتية'),
    ]
    STATUSES = [
        ('active',   'نشطة'),
        ('resolved', 'منتهية'),
    ]
    ALERT_TYPES = [
        # 🔴 حرجة
        ('NO_PAYMENT_30D',      'بدون دفعة 30+ يوم'),
        ('NO_SPONSOR_30D',      'بدون كافل 30+ يوم'),
        ('LATE_PAYMENT_7D',     'دفعات متأخرة 7+ أيام'),
        ('DISABLED_SPONSORED',  'معطّل ومكفول'),
        ('SPONSOR_NO_PAY_2M',   'كافل لم يدفع شهرين'),
        ('SPONSOR_REMOVED_14D', 'فقد الكافل 14+ يوم'),
        # 🟠 عالية
        ('PENDING_REQ_7D',      'طلبات معلّقة 7+ أيام'),
        ('NO_LOGIN_60D',        'لم يسجل دخولاً 60+ يوم'),
        ('SPECIAL_NO_AID_60D',  'ذوو احتياجات بدون مساعدة 60+ يوم'),
        ('HIGH_UNSPONSORED',    'غير مكفولين تجاوز 20%'),
        ('SPONSOR_3_LATE',      'كافل 3+ دفعات متأخرة'),
        ('PROFILE_OUTDATED_6M', 'ملف لم يُحدَّث 6 أشهر'),
        # 🟡 متوسطة
        ('NO_AIDS_THIS_MONTH',  'لا مساعدات هذا الشهر'),
        ('NO_PAYS_THIS_MONTH',  'لا دفعات هذا الشهر'),
        ('NEW_BENEFICIARY_24H', 'مستفيد جديد 24 ساعة'),
        ('NEW_SPONSOR_24H',     'كافل جديد 24 ساعة'),
        ('USER_DISABLED_7D',    'تعطيل حساب آخر 7 أيام'),
        ('AIDS_DROP_50',        'انخفاض المساعدات 50%'),
        ('SPONSOR_CHANGED_7D',  'تغيير كافل آخر 7 أيام'),
        # 🟢 معلوماتية
        ('ANNIVERSARY_1Y',      'ذكرى سنة على الاعتماد'),
        ('NO_MSG_30D',          'لم يُرسَل له رسالة 30+ يوم'),
        ('SPONSOR_5_BENE',      'كافل لديه 5+ مستفيدين'),
        ('PENDING_COUNT_10',    '10+ طلبات معلّقة'),
        ('END_MONTH_PENDING',   'آخر 3 أيام ودفعات معلّقة'),
        ('MONTHLY_SUMMARY',     'ملخص أسبوعي'),
    ]

    alert_type = models.CharField(
        max_length=50,
        choices=ALERT_TYPES,
        verbose_name='نوع التنبيه',
    )
    level = models.CharField(
        max_length=10,
        choices=LEVELS,
        default='info',
        verbose_name='المستوى',
    )
    status = models.CharField(
        max_length=10,
        choices=STATUSES,
        default='active',
        verbose_name='الحالة',
    )
    title = models.CharField(
        max_length=200,
        verbose_name='العنوان',
    )
    message = models.TextField(
        verbose_name='الرسالة',
    )

    # ── المستخدم المعني (اسمه + نوعه من user_type) ──
    target_user = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='smart_alerts',
        verbose_name='المستخدم المعني',
        help_text='الشخص المتعلق بالتنبيه — اسمه ونوعه (orphan/family/special/sponsor)',
    )

    action_url = models.CharField(
        max_length=300,
        null=True, blank=True,
        verbose_name='رابط الإجراء',
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='بيانات إضافية',
        help_text='أي بيانات إضافية مرتبطة بالتنبيه (JSON)',
    )

    # ── الأدمن الذي أغلق التنبيه + وقت الإغلاق ──
    dismissed_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='dismissed_alerts',
        verbose_name='أُغلق بواسطة',
        help_text='اسم الأدمن الذي أغلق هذا التنبيه',
    )
    dismissed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='وقت الإغلاق',
        help_text='الوقت الفعلي الذي تم فيه إغلاق التنبيه',
    )

    # ── الوقت الفعلي لحدوث التنبيه ──
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت حدوث التنبيه',
        help_text='الوقت الفعلي الذي تم فيه رصد هذا التنبيه',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخر تحديث',
    )

    class Meta:
        db_table            = 'core_smart_alerts'
        ordering            = ['-created_at']
        verbose_name        = 'تنبيه ذكي'
        verbose_name_plural = 'التنبيهات الذكية'
        indexes = [
            models.Index(fields=['status',     'level']),
            models.Index(fields=['alert_type', 'target_user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        user_info = f' — {self.target_user.get_full_name()}' if self.target_user else ''
        return f'[{self.get_level_display()}] {self.title}{user_info}'

    def dismiss(self, admin_user):
        """إغلاق التنبيه مع تسجيل الأدمن ووقت الإغلاق"""
        from django.utils import timezone
        self.status       = 'resolved'
        self.dismissed_by = admin_user
        self.dismissed_at = timezone.now()
        self.save(update_fields=['status', 'dismissed_by', 'dismissed_at'])

    @property
    def target_user_type_label(self):
        """نوع المستخدم المعني بالعربية"""
        if not self.target_user:
            return '—'
        TYPES = {
            'orphan':  'يتيم',
            'family':  'أسرة',
            'special': 'ذوو احتياجات',
            'sponsor': 'كافل',
            'admin':   'أدمن',
        }
        return TYPES.get(self.target_user.user_type, self.target_user.user_type)

    @property
    def level_color(self):
        """لون المستوى للعرض"""
        COLORS = {
            'critical': '#c53030',
            'high':     '#b45309',
            'medium':   '#b45309',
            'info':     '#1a7a4a',
        }
        return COLORS.get(self.level, '#6b7280')

    @property
    def is_active(self):
        return self.status == 'active'

# ==================== سجل النشاط ====================

class ActivityLog(models.Model):

    ACTIONS = [
        ('LOGIN',         'تسجيل دخول'),
        ('LOGOUT',        'تسجيل خروج'),
        ('REGISTER',      'تسجيل جديد'),
        ('UPDATE',        'تعديل بيانات'),
        ('DELETE',        'حذف'),
        ('EXPORT',        'تصدير'),
        ('VIEW',          'عرض'),
        ('MESSAGE',       'رسالة'),
        ('OTP',           'طلب OTP'),
        ('APPROVE',       'موافقة'),
        ('REJECT',        'رفض'),
        ('RECEIPT',       'وصل مالي'),
        ('PAYMENT',       'دفعة'),
        ('FAILED_LOGIN',  'دخول فاشل'),
        ('BLOCKED',       'حجب'),
    ]

    user         = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='logs')
    action       = models.CharField(max_length=20, choices=ACTIONS,
                                    verbose_name='الإجراء')
    target_model = models.CharField(max_length=100, null=True, blank=True,
                                    verbose_name='النموذج المستهدف')
    target_id    = models.CharField(max_length=100, null=True, blank=True,
                                    verbose_name='ID المستهدف')
    description  = models.TextField(verbose_name='التفاصيل')
    old_value    = models.JSONField(null=True, blank=True, verbose_name='القيمة القديمة')
    new_value    = models.JSONField(null=True, blank=True, verbose_name='القيمة الجديدة')
    ip_address   = models.GenericIPAddressField(null=True, blank=True,
                                                verbose_name='عنوان IP')
    user_agent   = models.TextField(null=True, blank=True,
                                    verbose_name='معلومات المتصفح')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'core_activity_logs'
        ordering            = ['-created_at']
        verbose_name        = 'سجل نشاط'
        verbose_name_plural = 'سجلات النشاط'

    def __str__(self):
        return f"{self.user} — {self.get_action_display()} — {self.created_at:%Y-%m-%d %H:%M}"


# ==================== الشكاوى ====================

class Complaint(models.Model):

    name       = models.CharField(max_length=100, verbose_name='الاسم')

    # الجوال — كود الدولة من Phone Picker API
    phone_country = models.CharField(max_length=10, default='+970',
                                     verbose_name='كود الدولة')
    phone      = models.CharField(max_length=20, verbose_name='رقم التواصل')

    email      = models.EmailField(verbose_name='البريد الإلكتروني')
    subject    = models.CharField(max_length=200, verbose_name='العنوان')
    message    = models.TextField(max_length=700, verbose_name='الرسالة')

    # حالة الشكوى
    is_seen    = models.BooleanField(default=False, verbose_name='تم المشاهدة')
    is_replied = models.BooleanField(default=False, verbose_name='تم الرد')
    reply_text = models.TextField(null=True, blank=True, verbose_name='نص الرد')
    replied_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='replied_complaints',
                                   verbose_name='رد بواسطة')
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name='وقت الرد')

    # معلومات إضافية
    ip_address = models.GenericIPAddressField(null=True, blank=True,
                                              verbose_name='عنوان IP')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'core_complaints'
        ordering            = ['-created_at']
        verbose_name        = 'شكوى'
        verbose_name_plural = 'الشكاوى'

    def get_full_phone(self):
        return f"{self.phone_country}{self.phone}"

    def __str__(self):
        return f"{self.name} — {self.subject}"


# ==================== FAQ ====================

class FAQ(models.Model):

    TARGET = [
        ('all',     'الجميع'),
        ('sponsor', 'الكفلاء'),
        ('orphan',  'الأيتام'),
    ]

    question   = models.CharField(max_length=500, verbose_name='السؤال')
    answer     = models.TextField(verbose_name='الجواب')
    target     = models.CharField(max_length=10, choices=TARGET,
                                  default='all', verbose_name='الموجّه إلى')
    order      = models.PositiveIntegerField(default=0, verbose_name='الترتيب')
    is_active  = models.BooleanField(default=True, verbose_name='نشط')
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                   null=True, related_name='faqs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'core_faq'
        ordering            = ['order', 'created_at']
        verbose_name        = 'سؤال شائع'
        verbose_name_plural = 'الأسئلة الشائعة'

    def __str__(self):
        return self.question


# ==================== إعدادات النظام ====================




# ==================== الرسائل المباشرة ====================

class DirectMessage(models.Model):
    sender     = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='sent_direct_messages',
                                   verbose_name='المُرسِل')
    recipient  = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='received_direct_messages',
                                   verbose_name='المُستقبِل')
    message    = models.TextField(verbose_name='الرسالة')
    is_read    = models.BooleanField(default=False, verbose_name='مقروءة')
    created_at = models.DateTimeField(auto_now_add=True)

    attachment = models.FileField(upload_to='messages/attachments/', null=True, blank=True)
    is_delivered = models.BooleanField(default=False)

    class Meta:
        db_table            = 'core_direct_messages'
        ordering            = ['created_at']
        verbose_name        = 'رسالة مباشرة'
        verbose_name_plural = 'الرسائل المباشرة'

    def __str__(self):
        return f"{self.sender.get_short_name()} → {self.recipient.get_short_name()}"


# ==================== ملاحظات المستخدمين ====================

class UserNote(models.Model):
    user       = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='notes', verbose_name='المستخدم'
    )
    admin      = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, related_name='written_notes',
        verbose_name='الأدمن'
    )
    note       = models.TextField(verbose_name='الملاحظة')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'core_user_notes'
        ordering            = ['-created_at']
        verbose_name        = 'ملاحظة'
        verbose_name_plural = 'الملاحظات'

    def __str__(self):
        return f'{self.user.get_short_name()} — {self.created_at:%Y-%m-%d}'


# ==================== المدفوعات ====================

class Payment(models.Model):

    STATUS = [
        ('paid',    'مدفوعة'),
        ('pending', 'معلّقة'),
        ('late',    'متأخرة'),
    ]

    PAID_BY = [
        ('sponsor',  'كافل'),
        ('admin',    'إدارة'),
        ('external', 'جهة خارجية'),
    ]

    beneficiary  = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='payments', verbose_name='المستفيد'
    )
    sponsor      = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sponsor_payments',
        verbose_name='الكافل'
    )
    amount_ils   = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='المبلغ بالشيقل'
    )
    amount_usd   = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='المبلغ بالدولار'
    )
    paid_by      = models.CharField(
        max_length=20, choices=PAID_BY,
        default='sponsor', verbose_name='مصدر الدفع'
    )
    paid_by_note = models.CharField(
        max_length=200, null=True, blank=True,
        verbose_name='اسم الجهة إذا كانت خارجية'
    )
    status       = models.CharField(
        max_length=20, choices=STATUS,
        default='paid', verbose_name='الحالة'
    )
    note         = models.TextField(
        null=True, blank=True, verbose_name='ملاحظة'
    )
    receipt      = models.ForeignKey(
        'sponsor.PaymentReceipt', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        verbose_name='الوصل المرتبط'
    )
    date         = models.DateField(verbose_name='تاريخ الدفعة')
    created_by   = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, related_name='created_payments',
        verbose_name='أضافها'
    )
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'core_payments'
        ordering            = ['-date']
        verbose_name        = 'دفعة'
        verbose_name_plural = 'الدفعات'

    def __str__(self):
        return f'{self.beneficiary.get_short_name()} — {self.amount_ils}₪ — {self.date}'


# ==================== المساعدات ====================

class Aid(models.Model):

    AID_TYPES = [
        ('food',      'غذائية'),
        ('medical',   'طبية'),
        ('financial', 'مالية'),
        ('clothing',  'ملابس'),
        ('furniture', 'أثاث'),
        ('education', 'تعليمية'),
        ('other',     'أخرى'),
    ]

    beneficiary = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='aids', verbose_name='المستفيد'
    )
    name        = models.CharField(
        max_length=200, verbose_name='اسم المساعدة'
    )
    aid_type    = models.CharField(
        max_length=20, choices=AID_TYPES,
        default='other', verbose_name='نوع المساعدة'
    )
    quantity    = models.PositiveIntegerField(
        default=1, verbose_name='العدد / الكمية'
    )
    provider    = models.CharField(
        max_length=200, verbose_name='الجهة المقدمة'
    )
    date        = models.DateField(verbose_name='تاريخ المساعدة')
    note        = models.TextField(
        null=True, blank=True, verbose_name='ملاحظة'
    )
    created_by  = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, related_name='created_aids',
        verbose_name='أضافها'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = 'core_aids'
        ordering            = ['-date']
        verbose_name        = 'مساعدة'
        verbose_name_plural = 'المساعدات'

    def __str__(self):
        return f'{self.beneficiary.get_short_name()} — {self.name} — {self.date}'


class SponsorReport(models.Model):

    STATUS_CHOICES = [
        ('sent',   'تم الإرسال'),
        ('failed', 'فشل الإرسال'),
    ]

    # ── الكافل والفترة ──
    sponsor      = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='sponsor_reports',
        verbose_name='الكافل',
    )
    period_year  = models.IntegerField(verbose_name='سنة التقرير')
    period_month = models.IntegerField(verbose_name='شهر التقرير')

    # ── الملف ──
    pdf_file = models.FileField(
        upload_to='sponsor_reports/%Y/%m/',
        verbose_name='ملف PDF',
        null=True, blank=True,
    )

    # ── معلومات الإرسال ──
    is_auto  = models.BooleanField(
        default=False,
        verbose_name='إرسال تلقائي',
        help_text='True = أرسله النظام تلقائياً | False = أرسله أدمن يدوياً',
    )
    sent_by  = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sent_reports',
        verbose_name='أرسله',
        help_text='اسم الأدمن الذي أرسل التقرير — فارغ إذا كان تلقائياً',
    )
    sent_at  = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الإرسال',
    )

    # ── حالة الإرسال ──
    status    = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='sent',
        verbose_name='حالة الإرسال',
    )
    error_msg = models.TextField(
        null=True, blank=True,
        verbose_name='رسالة الخطأ',
        help_text='سبب الفشل في حال فشل الإرسال',
    )

    class Meta:
        db_table         = 'core_sponsor_reports'
        ordering         = ['-sent_at']
        unique_together  = ('sponsor', 'period_year', 'period_month')
        verbose_name     = 'تقرير كافل'
        verbose_name_plural = 'تقارير الكفلاء'

    def __str__(self):
        return f'تقرير {self.sponsor.get_full_name()} — {self.period_month:02d}/{self.period_year}'

    @property
    def period_label(self):
        """مثال: 01/2026"""
        return f'{self.period_month:02d}/{self.period_year}'

    @property
    def sender_label(self):
        """من أرسل التقرير"""
        if self.is_auto:
            return 'النظام تلقائياً'
        if self.sent_by:
            return self.sent_by.get_full_name() or self.sent_by.username
        return '—'

class ComplaintNote(models.Model):
    complaint  = ForeignKey(Complaint, on_delete=CASCADE, related_name='notes')
    note       = TextField()
    admin      = ForeignKey(CustomUser, on_delete=SET_NULL, null=True)
    created_at = DateTimeField(auto_now_add=True)


class SystemSettings(models.Model):
    key         = models.CharField(max_length=100, unique=True, verbose_name='المفتاح')
    value       = models.TextField(verbose_name='القيمة')
    description = models.CharField(max_length=300, null=True, blank=True, verbose_name='الوصف')
    updated_at  = models.DateTimeField(auto_now=True)
    updated_by  = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='settings_updates'
    )

    class Meta:
        db_table            = 'core_system_settings'
        verbose_name        = 'إعداد النظام'
        verbose_name_plural = 'إعدادات النظام'

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get(cls, key, default=None):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, key, value, user=None):
        obj, _ = cls.objects.get_or_create(key=key)
        obj.value      = value
        obj.updated_by = user
        obj.save()
        return obj