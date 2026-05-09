from django.db import models
from core.models import CustomUser


# ==================== ملف الكافل ====================

class SponsorProfile(models.Model):

    GENDER = [
        ('ذكر',  'ذكر'),
        ('أنثى', 'أنثى'),
    ]

    JOBS = [
        ('موظف حكومي',    'موظف حكومي'),
        ('موظف خاص',      'موظف خاص'),
        ('تاجر',          'تاجر'),
        ('طبيب',          'طبيب'),
        ('مهندس',         'مهندس'),
        ('محامي',         'محامي'),
        ('معلم',          'معلم'),
        ('رجل أعمال',     'رجل أعمال'),
        ('متقاعد',        'متقاعد'),
        ('أخرى',          'أخرى'),
    ]

    user             = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                            related_name='sponsor_profile')
    # الصورة الشخصية
    photo            = models.ImageField(upload_to='sponsors/photos/',
                                         null=True, blank=True, verbose_name='الصورة الشخصية')

    # البيانات الشخصية
    gender           = models.CharField(max_length=10, choices=GENDER,
                                        null=True, blank=True, verbose_name='الجنس')
    nationality      = models.CharField(max_length=100, default='فلسطينية',
                                        verbose_name='الجنسية')
    job              = models.CharField(max_length=50, choices=JOBS,
                                        null=True, blank=True, verbose_name='المهنة')
    country          = models.CharField(max_length=100, null=True, blank=True,
                                        verbose_name='الدولة')
    city             = models.CharField(max_length=100, null=True, blank=True,
                                        verbose_name='المدينة')

    # أرقام التواصل
    phone_country    = models.CharField(max_length=10, default='+970',
                                        verbose_name='كود الدولة')
    phone            = models.CharField(max_length=20, null=True, blank=True,
                                        verbose_name='رقم الجوال')
    whatsapp_country = models.CharField(max_length=10, default='+970',
                                        verbose_name='كود واتساب')
    whatsapp         = models.CharField(max_length=20, null=True, blank=True,
                                        verbose_name='رقم الواتساب')

    # صلاحية التواصل المباشر
    can_contact      = models.BooleanField(default=False,
                                           verbose_name='مسموح بالتواصل المباشر')

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table         = 'sponsor_profiles'
        verbose_name     = 'ملف كافل'
        verbose_name_plural = 'ملفات الكفلاء'

    def __str__(self):
        return self.user.get_full_name()

    def total_paid_shekel(self):
        return self.receipts.filter(
            status='موافق'
        ).aggregate(
            total=models.Sum('amount_shekel')
        )['total'] or 0

    def total_paid_dollar(self):
        return self.receipts.filter(
            status='موافق'
        ).aggregate(
            total=models.Sum('amount_dollar')
        )['total'] or 0

    def sponsored_count(self):
        from beneficiary import OrphanForm, SpecialNeedsForm, FamilyForm
        return (
            OrphanForm.objects.filter(sponsor=self).count() +
            SpecialNeedsForm.objects.filter(sponsor=self).count() +
            FamilyForm.objects.filter(sponsor=self).count()
        )


# ==================== الوصولات المالية ====================

class PaymentReceipt(models.Model):

    STATUS = [
        ('بانتظار المراجعة', 'بانتظار المراجعة'),
        ('موافق',            'موافق'),
        ('مرفوض',            'مرفوض'),
    ]

    CURRENCY_CHOICES = [
        ('ILS', 'شيقل إسرائيلي'),
        ('USD', 'دولار أمريكي'),
        ('JOD', 'دينار أردني'),
        ('SAR', 'ريال سعودي'),
        ('EGP', 'جنيه مصري'),
    ]

    # ── الكافل والمستفيد ──
    sponsor          = models.ForeignKey(
        SponsorProfile, on_delete=models.CASCADE,
        related_name='receipts', verbose_name='الكافل'
    )
    beneficiary      = models.ForeignKey(
        'core.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='received_receipts',
        verbose_name='المستفيد'
    )

    # ── معرّفات الوصل ──
    system_ref       = models.CharField(
        max_length=120, unique=True, blank=True,
        verbose_name='الرقم المرجعي للنظام'
    )
    unique_number    = models.CharField(
        max_length=100,
        verbose_name='رقم الوصل الفريد'
    )
    sender_name      = models.CharField(
        max_length=200, blank=True,
        verbose_name='اسم المُرسِل'
    )

    # ── المبالغ ──
    amount_original  = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='المبلغ الأصلي'
    )
    currency         = models.CharField(
        max_length=5, choices=CURRENCY_CHOICES, default='USD',
        verbose_name='العملة'
    )
    amount_shekel    = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='المبلغ بالشيقل'
    )
    amount_dollar    = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='المبلغ بالدولار'
    )

    # ── الصورة والتاريخ ──
    receipt_date     = models.DateField(
        null=True, blank=True,
        verbose_name='تاريخ الوصل'
    )
    receipt_image    = models.ImageField(
        upload_to='sponsors/receipts/',
        null=True, blank=True,
        verbose_name='صورة الوصل'
    )

    # ── الحالة والمراجعة ──
    status           = models.CharField(
        max_length=25, choices=STATUS,
        default='بانتظار المراجعة',
        verbose_name='الحالة'
    )
    reject_reason    = models.TextField(
        null=True, blank=True,
        verbose_name='سبب الرفض'
    )
    reviewed_by      = models.ForeignKey(
        'core.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_receipts',
        verbose_name='راجعه'
    )
    reviewed_at      = models.DateTimeField(
        null=True, blank=True,
        verbose_name='وقت المراجعة'
    )
    notes            = models.TextField(
        null=True, blank=True,
        verbose_name='ملاحظات الإدارة'
    )

    # ── توقيت ──
    submitted_at     = models.DateTimeField(
        auto_now_add=True,
        verbose_name='وقت الإرسال'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'sponsor_receipts'
        ordering            = ['-submitted_at']
        verbose_name        = 'وصل مالي'
        verbose_name_plural = 'الوصولات المالية'

    def __str__(self):
        return f"{self.system_ref or self.pk} — {self.amount_original} {self.currency} — {self.status}"

    def save(self, *args, **kwargs):
        # توليد الرقم المرجعي تلقائياً إذا لم يكن موجوداً
        if not self.system_ref and self.sponsor_id:
            try:
                from django.utils import timezone
                user     = self.sponsor.user
                username = user.username or str(self.sponsor_id)
                date_str = timezone.now().strftime('%Y%m%d')
                base_ref = f"REF-{username}-{date_str}"
                # تأكد من الفرادة
                counter  = 1
                ref      = base_ref
                while PaymentReceipt.objects.filter(system_ref=ref).exists():
                    ref = f"{base_ref}-{counter}"
                    counter += 1
                self.system_ref = ref
            except Exception:
                import uuid
                self.system_ref = f"REF-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)


# ==================== جدولة الدفعات ====================

class PaymentSchedule(models.Model):

    BENEFICIARY_TYPE = [
        ('orphan',  'يتيم'),
        ('special', 'ذوو احتياجات'),
        ('family',  'أسرة'),
    ]

    sponsor          = models.ForeignKey(
        SponsorProfile, on_delete=models.CASCADE,
        related_name='schedules', verbose_name='الكافل'
    )
    beneficiary      = models.ForeignKey(
        'core.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_schedules',
        verbose_name='المستفيد'
    )
    beneficiary_type = models.CharField(
        max_length=10, choices=BENEFICIARY_TYPE,
        verbose_name='نوع المستفيد'
    )
    amount_shekel    = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name='المبلغ الشهري (شيقل)'
    )
    amount_dollar    = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name='المبلغ الشهري (دولار)'
    )
    currency         = models.CharField(
        max_length=5, default='USD',
        verbose_name='العملة الأصلية'
    )
    amount_original  = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name='المبلغ الشهري بالعملة الأصلية'
    )
    due_day          = models.PositiveIntegerField(
        default=1, verbose_name='يوم الاستحقاق من الشهر'
    )
    is_active        = models.BooleanField(
        default=True, verbose_name='نشط'
    )
    start_date       = models.DateField(verbose_name='تاريخ البداية')
    end_date         = models.DateField(
        null=True, blank=True, verbose_name='تاريخ الانتهاء'
    )
    notes            = models.TextField(
        null=True, blank=True, verbose_name='ملاحظات'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'sponsor_payment_schedules'
        verbose_name        = 'جدولة دفعة'
        verbose_name_plural = 'جداول الدفعات'
        ordering            = ['-created_at']

    def __str__(self):
        bene = self.beneficiary.get_full_name() if self.beneficiary else '—'
        return f"{self.sponsor} → {bene} — {self.amount_shekel}₪/شهر"


# ==================== الرسائل المباشرة ====================

class Message(models.Model):

    sender      = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                    related_name='sponsor_sent_messages',
                                    verbose_name='المُرسِل')
    recipient   = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                    related_name='sponsor_received_messages',
                                    verbose_name='المُستقبِل')
    message     = models.TextField(verbose_name='الرسالة')
    is_read     = models.BooleanField(default=False, verbose_name='مقروءة')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'sponsor_messages'
        ordering     = ['created_at']
        verbose_name = 'رسالة'
        verbose_name_plural = 'الرسائل'

    def __str__(self):
        return f"{self.sender} → {self.recipient}"


# ==================== الإعلانات ====================

class Announcement(models.Model):

    TARGET = [
        ('all',     'الجميع'),
        ('sponsors','الكفلاء فقط'),
        ('orphans', 'الأيتام فقط'),
    ]

    title       = models.CharField(max_length=200, verbose_name='عنوان الإعلان')
    content     = models.TextField(verbose_name='محتوى الإعلان')
    target      = models.CharField(max_length=10, choices=TARGET,
                                   default='all', verbose_name='الموجّه إلى')
    created_by  = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                    null=True, related_name='announcements')
    is_active   = models.BooleanField(default=True, verbose_name='نشط')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'sponsor_announcements'
        ordering     = ['-created_at']
        verbose_name = 'إعلان'
        verbose_name_plural = 'الإعلانات'

    def __str__(self):
        return self.title