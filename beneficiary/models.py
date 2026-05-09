from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
from core.models import CustomUser


# ==================== ثوابت مشتركة ====================

CITIES = [
    ('رفح',        'رفح'),
    ('خانيونس',    'خانيونس'),
    ('القرارة',    'القرارة'),
    ('دير البلح',  'دير البلح'),
    ('الزوايدة',   'الزوايدة'),
    ('النصيرات',   'النصيرات'),
    ('المغازي',    'المغازي'),
    ('البريج',     'البريج'),
    ('مدينة غزة',  'مدينة غزة'),
    ('شمال غزة',   'شمال غزة'),
    ('شرق غزة',    'شرق غزة'),
    ('غرب غزة',    'غرب غزة'),
    ('غير محدد',   'غير محدد'),
]

HEALTH_STATUS = [
    ('سليم',                   'سليم'),
    ('مرض مزمن',               'مرض مزمن'),
    ('ذوو احتياجات خاصة',      'ذوو احتياجات خاصة'),
    ('مصاب حرب',               'مصاب حرب'),
]

EDUCATION_LEVEL = [
    ('غير متعلم',   'غير متعلم'),
    ('رياض الأطفال','رياض الأطفال'),
    ('ابتدائي',     'ابتدائي'),
    ('إعدادي',      'إعدادي'),
    ('ثانوي',       'ثانوي'),
    ('جامعي',       'جامعي'),
    ('ماجستير',     'ماجستير'),
    ('دكتوراه',     'دكتوراه'),
]

SCHOOL_GRADE = [
    ('0',  'روضة'),
    ('1',  'الصف الأول'),
    ('2',  'الصف الثاني'),
    ('3',  'الصف الثالث'),
    ('4',  'الصف الرابع'),
    ('5',  'الصف الخامس'),
    ('6',  'الصف السادس'),
    ('7',  'الصف السابع'),
    ('8',  'الصف الثامن'),
    ('9',  'الصف التاسع'),
    ('10', 'الصف العاشر'),
    ('11', 'الصف الحادي عشر'),
    ('12', 'الصف الثاني عشر'),
]

HOUSING_TYPE = [
    ('خيمة',       'خيمة'),
    ('بيت باطون',  'بيت باطون'),
    ('بيت زينقو',  'بيت زينقو'),
]

HOUSING_OWNERSHIP = [
    ('ملك',   'ملك'),
    ('إيجار', 'إيجار'),
]

DEATH_REASON = [
    ('شهيد', 'شهيد'),
    ('مرض',  'مرض'),
    ('طبيعي','طبيعي'),
]

GUARDIAN_RELATION = [
    ('عم',   'عم/ـة'),
    ('خال',  'خال/ـة'),
    ('جد',   'جد/ة'),
    ('أخ',   'أخ'),
    ('أخت',  'أخت'),
    ('أخرى', 'أخرى'),
]

MARITAL_STATUS = [
    ('أعزب',   'أعزب'),
    ('متزوج',  'متزوج/ـة'),
    ('مطلق',   'مطلق/ـة'),
    ('أرمل',   'أرمل/ـة'),
]

FAMILY_RELATION = [
    ('أخ',   'أخ'),
    ('أخت',  'أخت'),
    ('أم',   'أم'),
    ('أب',   'أب'),
    ('أخرى', 'أخرى'),
]

ORPHAN_TYPE = [
    ('يتيم الأب',  'يتيم الأب'),
    ('يتيم الأم',  'يتيم الأم'),
    ('كلاهما',     'كلاهما'),
]

JOBS = [
    ('موظف حكومي',       'موظف حكومي'),
    ('موظف قطاع خاص',   'موظف قطاع خاص'),
    ('تاجر',             'تاجر'),
    ('طبيب',             'طبيب'),
    ('مهندس',            'مهندس'),
    ('محامٍ',             'محامٍ'),
    ('معلم/ـة',          'معلم/ـة'),
    ('ممرض/ـة',          'ممرض/ـة'),
    ('محاسب',            'محاسب'),
    ('صيدلاني',          'صيدلاني'),
    ('مقاول',            'مقاول'),
    ('سائق',             'سائق'),
    ('نجار',             'نجار'),
    ('حداد',             'حداد'),
    ('كهربائي',          'كهربائي'),
    ('سباك',             'سباك'),
    ('خياط',             'خياط'),
    ('حلاق',             'حلاق'),
    ('صاحب محل',         'صاحب محل'),
    ('مزارع',            'مزارع'),
    ('صياد',             'صياد'),
    ('عامل',             'عامل'),
    ('ربة بيت',          'ربة بيت'),
    ('طالب/ـة',          'طالب/ـة'),
    ('متقاعد',           'متقاعد'),
    ('رجل أعمال',        'رجل أعمال'),
    ('لا يعمل',          'لا يعمل'),
    ('أخرى',             'أخرى'),
]

id_validator = RegexValidator(
    regex  = r'^[984]\d{8}$',
    message= 'رقم الهوية يجب أن يكون 9 أرقام ويبدأ بـ 9 أو 8 أو 4'
)


# ==================== دالة مسار الصور ====================

def orphan_photo_path(instance, filename):
    return f'orphans/{instance.form_number}/{filename}'

def special_photo_path(instance, filename):
    return f'specials/{instance.form_number}/{filename}'

def family_photo_path(instance, filename):
    return f'families/{instance.form_number}/{filename}'

def doc_upload_path(instance, filename):
    return f'documents/{instance.__class__.__name__}/{filename}'


# ==================== استمارة اليتيم ====================

class OrphanForm(models.Model):

    STATUS_CHOICES = [
        ('مسودة',         'مسودة'),
        ('مرسلة',         'مرسلة'),
        ('قيد المراجعة',  'قيد المراجعة'),
        ('مقبولة',        'مقبولة'),
        ('تم التدقيق',    'تم التدقيق'),
        ('تم التكفل',     'تم التكفل'),
        ('مرفوضة',        'مرفوضة'),
    ]

    user        = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                       related_name='orphan_form')
    sponsor     = models.ForeignKey('sponsor.SponsorProfile', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='orphans')
    form_number = models.CharField(max_length=20, unique=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='مسودة')

    # ===== بيانات اليتيم =====
    first_name      = models.CharField(max_length=50,  verbose_name='الاسم الأول')
    father_name     = models.CharField(max_length=50,  verbose_name='اسم الأب')
    grand_name      = models.CharField(max_length=50,  verbose_name='اسم الجد')
    family_name     = models.CharField(max_length=50,  verbose_name='اسم العائلة')
    birth_date      = models.DateField(verbose_name='تاريخ الميلاد')
    id_number       = models.CharField(max_length=9, validators=[id_validator],
                                       verbose_name='رقم الهوية')
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,   default='PS')
    gender          = models.CharField(max_length=10,  choices=[('ذكر','ذكر'),('أنثى','أنثى')])
    orphan_type     = models.CharField(max_length=20,  choices=ORPHAN_TYPE,
                                       verbose_name='من فقد من الوالدين')
    health_status   = models.CharField(max_length=30,  choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20,  choices=EDUCATION_LEVEL)
    school_grade    = models.CharField(max_length=5,   choices=SCHOOL_GRADE,
                                       blank=True, null=True)
    school_name     = models.CharField(max_length=200, blank=True)
    photo           = models.ImageField(upload_to=orphan_photo_path,
                                        verbose_name='صورة اليتيم')

    # ===== العنوان الحالي =====
    current_city        = models.CharField(max_length=30, choices=CITIES)
    current_street      = models.CharField(max_length=200)
    current_landmark    = models.CharField(max_length=200)

    # ===== العنوان السابق =====
    previous_city       = models.CharField(max_length=30, choices=CITIES, blank=True)
    previous_street     = models.CharField(max_length=200, blank=True)
    previous_landmark   = models.CharField(max_length=200, blank=True)

    # ===== التواصل =====
    phone1          = models.CharField(max_length=20)
    phone1_country  = models.CharField(max_length=10, default='+970')
    phone2          = models.CharField(max_length=20, blank=True)
    phone2_country  = models.CharField(max_length=10, default='+970')
    whatsapp        = models.CharField(max_length=20)
    whatsapp_country= models.CharField(max_length=10, default='+970')

    # ===== السكن =====
    housing_type      = models.CharField(max_length=20, choices=HOUSING_TYPE)
    housing_ownership = models.CharField(max_length=10, choices=HOUSING_OWNERSHIP)
    monthly_rent      = models.DecimalField(max_digits=10, decimal_places=2,
                                            null=True, blank=True)

    # ===== القصة =====
    story = models.TextField(max_length=1000, verbose_name='قصة اليتيم')

    # ===== الكافل والتواصل =====
    sponsorship_date   = models.DateField(null=True, blank=True)
    allow_direct_comm  = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = 'beneficiary_orphan_forms'
        verbose_name = 'استمارة يتيم'

    def save(self, *args, **kwargs):
        if not self.form_number:
            last = OrphanForm.objects.order_by('-id').first()
            num  = (last.id + 1) if last else 1
            self.form_number = f'ORF-{num:05d}'
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'

    def get_short_name(self):
        return f'{self.first_name} {self.family_name}'

    def __str__(self):
        return f'{self.form_number} — {self.get_full_name()}'


# ==================== بيانات أم اليتيم ====================

class OrphanMother(models.Model):
    form            = models.OneToOneField(OrphanForm, on_delete=models.CASCADE,
                                           related_name='mother')
    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10, default='أنثى')
    is_alive        = models.BooleanField(default=True)
    death_date      = models.DateField(null=True, blank=True)
    death_reason    = models.CharField(max_length=20, choices=DEATH_REASON,
                                       blank=True)
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    job             = models.CharField(max_length=50,  choices=JOBS)
    monthly_income  = models.DecimalField(max_digits=10, decimal_places=2,
                                          default=0)

    class Meta:
        db_table     = 'beneficiary_orphan_mothers'
        verbose_name = 'بيانات الأم'

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'


# ==================== بيانات أب اليتيم ====================

class OrphanFather(models.Model):
    form            = models.OneToOneField(OrphanForm, on_delete=models.CASCADE,
                                           related_name='father')
    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10, default='ذكر')
    is_alive        = models.BooleanField(default=False)
    death_date      = models.DateField(null=True, blank=True)
    death_reason    = models.CharField(max_length=20, choices=DEATH_REASON, blank=True)
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    job             = models.CharField(max_length=50,  choices=JOBS)
    children_count  = models.PositiveIntegerField(default=0)
    income_before   = models.DecimalField(max_digits=10, decimal_places=2,
                                          null=True, blank=True)
    pension_after   = models.DecimalField(max_digits=10, decimal_places=2,
                                          null=True, blank=True)

    class Meta:
        db_table     = 'beneficiary_orphan_fathers'
        verbose_name = 'بيانات الأب'

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'


# ==================== المعيل الحالي (مشترك) ====================

class CurrentGuardian(models.Model):
    form_type = models.CharField(max_length=10,
                                 choices=[('orphan','يتيم'),('special','ذوو احتياجات'),
                                          ('family','أسرة')])
    form_id   = models.PositiveIntegerField()

    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10,
                                       choices=[('ذكر','ذكر'),('أنثى','أنثى')])
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    job             = models.CharField(max_length=50,  choices=JOBS)
    monthly_income  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    relation        = models.CharField(max_length=20, choices=GUARDIAN_RELATION)
    dependents      = models.PositiveIntegerField(default=1)

    class Meta:
        db_table     = 'beneficiary_current_guardians'
        verbose_name = 'المعيل الحالي'

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'


# ==================== أفراد الأسرة (مشترك) ====================

class FamilyMember(models.Model):
    form_type = models.CharField(max_length=10,
                                 choices=[('orphan','يتيم'),('special','ذوو احتياجات'),
                                          ('family','أسرة')])
    form_id   = models.PositiveIntegerField()

    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10,
                                       choices=[('ذكر','ذكر'),('أنثى','أنثى')])
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    school_grade    = models.CharField(max_length=5,  choices=SCHOOL_GRADE,
                                       blank=True, null=True)
    marital_status  = models.CharField(max_length=10, choices=MARITAL_STATUS)
    relation        = models.CharField(max_length=10, choices=FAMILY_RELATION)

    class Meta:
        db_table     = 'beneficiary_family_members'
        verbose_name = 'فرد من الأسرة'

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'


# ==================== استمارة ذوي الاحتياجات ====================

class SpecialNeedsForm(models.Model):

    STATUS_CHOICES = OrphanForm.STATUS_CHOICES

    user        = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                       related_name='special_form')
    sponsor     = models.ForeignKey('sponsor.SponsorProfile', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='specials')
    form_number = models.CharField(max_length=20, unique=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='مسودة')

    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10,
                                       choices=[('ذكر','ذكر'),('أنثى','أنثى')])
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    school_grade    = models.CharField(max_length=5,  choices=SCHOOL_GRADE,
                                       blank=True, null=True)
    school_name     = models.CharField(max_length=200, blank=True)
    photo           = models.ImageField(upload_to=special_photo_path)

    current_city        = models.CharField(max_length=30, choices=CITIES)
    current_street      = models.CharField(max_length=200)
    current_landmark    = models.CharField(max_length=200)
    previous_city       = models.CharField(max_length=30, choices=CITIES, blank=True)
    previous_street     = models.CharField(max_length=200, blank=True)
    previous_landmark   = models.CharField(max_length=200, blank=True)

    phone1          = models.CharField(max_length=20)
    phone1_country  = models.CharField(max_length=10, default='+970')
    phone2          = models.CharField(max_length=20, blank=True)
    phone2_country  = models.CharField(max_length=10, default='+970')
    whatsapp        = models.CharField(max_length=20)
    whatsapp_country= models.CharField(max_length=10, default='+970')

    housing_type      = models.CharField(max_length=20, choices=HOUSING_TYPE)
    housing_ownership = models.CharField(max_length=10, choices=HOUSING_OWNERSHIP)
    monthly_rent      = models.DecimalField(max_digits=10, decimal_places=2,
                                            null=True, blank=True)
    case_details      = models.TextField(max_length=1000)

    sponsorship_date  = models.DateField(null=True, blank=True)
    allow_direct_comm = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = 'beneficiary_special_forms'
        verbose_name = 'استمارة ذوو احتياجات'

    def save(self, *args, **kwargs):
        if not self.form_number:
            last = SpecialNeedsForm.objects.order_by('-id').first()
            num  = (last.id + 1) if last else 1
            self.form_number = f'SPF-{num:05d}'
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'

    def __str__(self):
        return f'{self.form_number} — {self.get_full_name()}'


# ==================== استمارة الأسرة ====================

class FamilyForm(models.Model):

    STATUS_CHOICES = OrphanForm.STATUS_CHOICES

    MARITAL_HEAD = [
        ('متزوج',  'متزوج/ـة'),
        ('أرمل',   'أرمل/ـة'),
        ('مطلق',   'مطلق/ـة'),
    ]

    user        = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                       related_name='family_form')
    sponsor     = models.ForeignKey('sponsor.SponsorProfile', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='families')
    form_number = models.CharField(max_length=20, unique=True, blank=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='مسودة')

    # ===== رب الأسرة =====
    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10,
                                       choices=[('ذكر','ذكر'),('أنثى','أنثى')])
    is_alive        = models.BooleanField(default=True)
    marital_status  = models.CharField(max_length=10, choices=MARITAL_HEAD)
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    job             = models.CharField(max_length=50,  choices=JOBS)
    photo           = models.ImageField(upload_to=family_photo_path)

    current_city        = models.CharField(max_length=30, choices=CITIES)
    current_street      = models.CharField(max_length=200)
    current_landmark    = models.CharField(max_length=200)
    previous_city       = models.CharField(max_length=30, choices=CITIES, blank=True)
    previous_street     = models.CharField(max_length=200, blank=True)
    previous_landmark   = models.CharField(max_length=200, blank=True)

    phone1          = models.CharField(max_length=20)
    phone1_country  = models.CharField(max_length=10, default='+970')
    phone2          = models.CharField(max_length=20, blank=True)
    phone2_country  = models.CharField(max_length=10, default='+970')
    whatsapp        = models.CharField(max_length=20)
    whatsapp_country= models.CharField(max_length=10, default='+970')

    housing_type        = models.CharField(max_length=20, choices=HOUSING_TYPE)
    housing_ownership   = models.CharField(max_length=10, choices=HOUSING_OWNERSHIP)
    monthly_rent        = models.DecimalField(max_digits=10, decimal_places=2,
                                              null=True, blank=True)
    family_members_count= models.PositiveIntegerField(default=1)
    sick_members_count  = models.PositiveIntegerField(default=0)
    general_status      = models.TextField(max_length=1000)

    sponsorship_date  = models.DateField(null=True, blank=True)
    allow_direct_comm = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table     = 'beneficiary_family_forms'
        verbose_name = 'استمارة أسرة'

    def save(self, *args, **kwargs):
        if not self.form_number:
            last = FamilyForm.objects.order_by('-id').first()
            num  = (last.id + 1) if last else 1
            self.form_number = f'FAM-{num:05d}'
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'

    def __str__(self):
        return f'{self.form_number} — {self.get_full_name()}'


# ==================== بيانات زوجة رب الأسرة ====================

class FamilyWife(models.Model):
    form            = models.OneToOneField(FamilyForm, on_delete=models.CASCADE,
                                           related_name='wife')
    first_name      = models.CharField(max_length=50)
    father_name     = models.CharField(max_length=50)
    grand_name      = models.CharField(max_length=50)
    family_name     = models.CharField(max_length=50)
    birth_date      = models.DateField()
    id_number       = models.CharField(max_length=9, validators=[id_validator])
    nationality     = models.CharField(max_length=100, default='فلسطينية')
    nationality_code= models.CharField(max_length=5,  default='PS')
    gender          = models.CharField(max_length=10, default='أنثى')
    health_status   = models.CharField(max_length=30, choices=HEALTH_STATUS)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVEL)
    photo           = models.ImageField(upload_to='families/wives/', blank=True, null=True)

    current_city      = models.CharField(max_length=30, choices=CITIES, blank=True)
    current_street    = models.CharField(max_length=200, blank=True)
    current_landmark  = models.CharField(max_length=200, blank=True)
    previous_city     = models.CharField(max_length=30, choices=CITIES, blank=True)
    previous_street   = models.CharField(max_length=200, blank=True)
    previous_landmark = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table     = 'beneficiary_family_wives'
        verbose_name = 'بيانات الزوجة'

    def get_full_name(self):
        return f'{self.first_name} {self.father_name} {self.grand_name} {self.family_name}'


# ==================== الدفعات ====================

class Payment(models.Model):
    BENE_TYPES = [
        ('orphan',  'يتيم'),
        ('special', 'ذوو احتياجات'),
        ('family',  'أسرة'),
    ]
    STATUS = [
        ('مدفوع', 'مدفوع'),
        ('معلق',  'معلق'),
        ('ملغي',  'ملغي'),
    ]

    beneficiary_type = models.CharField(max_length=10, choices=BENE_TYPES)
    beneficiary_id   = models.PositiveIntegerField()
    sponsor          = models.ForeignKey('sponsor.SponsorProfile', null=True, blank=True,
                                         on_delete=models.SET_NULL)
    amount_shekel    = models.DecimalField(max_digits=10, decimal_places=2)
    amount_dollar    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date     = models.DateField()
    description      = models.CharField(max_length=300, blank=True)
    status           = models.CharField(max_length=10, choices=STATUS, default='مدفوع')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table     = 'beneficiary_payments'
        ordering     = ['-payment_date']
        verbose_name = 'دفعة'


# ==================== المستندات ====================

class OrphanDocument(models.Model):
    DOC_TYPES = [
        ('هوية_الوصي',          'صورة هوية الوصي'),
        ('شهادة_ميلاد_الطفل',   'شهادة ميلاد الطفل'),
        ('شهادة_وفاة_الاب',     'شهادة وفاة الأب'),
        ('حجة_وصاية',           'حجة وصاية'),
        ('حجة_ترمل',            'حجة ترمل'),
        ('حجة_ولاية',           'حجة ولاية'),
        ('حجة_اعالة',           'حجة إعالة'),
        ('حجة_اقرار_حضانة',    'حجة إقرار حضانة'),
        ('شهادة_ميلاد_الاخوة', 'شهادة ميلاد الأخوة'),
    ]
    REQUIRED = ['هوية_الوصي','شهادة_ميلاد_الطفل','شهادة_وفاة_الاب','حجة_وصاية']

    form     = models.ForeignKey(OrphanForm, on_delete=models.CASCADE,
                                  related_name='documents')
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    file     = models.FileField(upload_to='orphan_docs/')

    class Meta:
        db_table = 'beneficiary_orphan_documents'


class SpecialDocument(models.Model):
    DOC_TYPES = [
        ('هوية_المعيل',         'هوية المعيل'),
        ('هوية_الاب',           'هوية الأب'),
        ('هوية_الام',           'هوية الأم'),
        ('شهادة_ميلاد_الشخص',  'شهادة ميلاد الشخص'),
        ('التقرير_الطبي',       'التقرير الطبي'),
        ('هوية_المريض',         'هوية المريض'),
    ]
    REQUIRED = ['هوية_المعيل','هوية_الاب','هوية_الام',
                'شهادة_ميلاد_الشخص','التقرير_الطبي','هوية_المريض']

    form     = models.ForeignKey(SpecialNeedsForm, on_delete=models.CASCADE,
                                  related_name='documents')
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    file     = models.FileField(upload_to='special_docs/')

    class Meta:
        db_table = 'beneficiary_special_documents'


class FamilyDocument(models.Model):
    DOC_TYPES = [
        ('هوية_الام',   'هوية الأم'),
        ('هوية_الاب',   'هوية الأب'),
        ('هوية_المعيل', 'هوية المعيل'),
        ('تقارير_طبية', 'تقارير طبية'),
    ]
    REQUIRED = ['هوية_الام','هوية_الاب','هوية_المعيل']

    form     = models.ForeignKey(FamilyForm, on_delete=models.CASCADE,
                                  related_name='documents')
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    file     = models.FileField(upload_to='family_docs/')

    class Meta:
        db_table = 'beneficiary_family_documents'