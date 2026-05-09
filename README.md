<div align="center">

<img src="https://img.shields.io/badge/Django-4.x-092E20?style=for-the-badge&logo=django&logoColor=white"/>
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white"/>
<img src="https://img.shields.io/badge/Bootstrap-5-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white"/>
<img src="https://img.shields.io/badge/WeasyPrint-PDF-1a7a4a?style=for-the-badge"/>

# 🌿 منصة رُحَمَاء
### Ruhamaa — Palestinian Charity Management Platform

**منصة متكاملة لإدارة الكفالات والوصولات المالية لجمعية نسائم فلسطين الخيرية**

[🌐 العرض التجريبي](#) • [📖 التوثيق](#التوثيق) • [🐛 الإبلاغ عن مشكلة](https://github.com/AlaaAlhoot/ruhamaa/issues)

</div>

---

## 📋 جدول المحتويات

- [نبذة عن المشروع](#نبذة-عن-المشروع)
- [المميزات الرئيسية](#المميزات-الرئيسية)
- [التقنيات المستخدمة](#التقنيات-المستخدمة)
- [هيكل المشروع](#هيكل-المشروع)
- [المتطلبات](#المتطلبات)
- [التثبيت والتشغيل](#التثبيت-والتشغيل)
- [المستخدمون والصلاحيات](#المستخدمون-والصلاحيات)
- [لقطات الشاشة](#لقطات-الشاشة)
- [المساهمة](#المساهمة)
- [المطور](#المطور)

---

## 🌿 نبذة عن المشروع

**منصة رُحَمَاء** هي نظام إدارة خيري متكامل طُوِّر خصيصاً لـ **جمعية نسائم فلسطين الخيرية**، يهدف إلى تنظيم وتوثيق عمليات الكفالة والدعم المالي للمستفيدين في غزة.

تتيح المنصة للكفلاء تسجيل وصولاتهم المالية وتتبع حالتها، بينما تمنح الإدارة أدوات متقدمة للمراجعة والموافقة وإصدار السندات الرسمية، مع دعم كامل للغة العربية واتجاه RTL.

---

## ✨ المميزات الرئيسية

### 👥 إدارة المستفيدين
- دعم أربعة أنواع من المستفيدين: **الأيتام، الأسر، ذوو الاحتياجات الخاصة، الكفلاء**
- تسجيل متعدد الخطوات مع التحقق الفوري من التكرار
- أرقام تسجيل فريدة لكل مستفيد
- ربط المستفيدين بالكفلاء بشكل مباشر

### 💳 نظام الوصولات المالية
- رفع الوصولات مع صورة وبيانات كاملة
- تحويل تلقائي للمبالغ بين العملات (دولار، شيقل، دينار، ريال، جنيه)
- تتبع حالة الوصل: **بانتظار المراجعة / موافق / مرفوض**
- إمكانية إعادة إرسال الوصولات المرفوضة مع التعديل
- التحقق الفوري من تكرار رقم الوصل

### 📄 السندات المالية الرسمية
- توليد سندات PDF احترافية بـ WeasyPrint
- علامات مائية أمنية ونمط خلفية لمنع التزوير
- شريط تحقق أمني مع رقم مرجعي فريد
- تصدير PDF مباشر مع شريط تقدم تفاعلي

### 🛡️ لوحة تحكم الإدارة
- مراجعة وقبول ورفض الوصولات مع إشعارات فورية
- إحصائيات شاملة: إجمالي الكفالات، المبالغ الشهرية، عدد المستفيدين
- بحث وفلترة متقدمة (بالحالة، العملة، التاريخ، الاسم)
- تصدير البيانات إلى Excel بتنسيق احترافي
- نظام سجل نشاط (Activity Log) لتتبع كل العمليات
- وضع الصيانة Maintenance Mode

### 📧 الإشعارات والتواصل
- إشعارات بريد إلكتروني تلقائية عند الموافقة أو الرفض
- نظام إشعارات داخلي في المنصة
- رسائل مخصصة باللغة العربية

### 🌐 دعم ثنائي اللغة
- واجهة عربية كاملة مع RTL
- دعم اللغة الإنجليزية
- نظام ترجمة Django i18n مع ملفات `.po`

---

## 🛠️ التقنيات المستخدمة

| الفئة | التقنية |
|-------|---------|
| **Backend** | Python 3.10+, Django 4.x |
| **قاعدة البيانات** | MySQL 8.0 |
| **Frontend** | Bootstrap 5, JavaScript ES6+, HTML5, CSS3 |
| **PDF** | WeasyPrint |
| **Excel** | openpyxl |
| **الخادم** | Nginx + Gunicorn |
| **SSL** | Let's Encrypt |
| **الاستضافة** | Hostinger VPS / PythonAnywhere |
| **الأمان** | Django CSRF, Custom Decorators, Activity Logging |

---

## 🗂️ هيكل المشروع

```
ruhamaa/
│
├── core/                        # التطبيق الأساسي
│   ├── models.py                # CustomUser, Payment, Notification, SystemSettings
│   ├── utils.py                 # log_activity, create_notification, get_exchange_rates
│   └── views.py
│
├── admin_panel/                 # لوحة تحكم الإدارة
│   ├── views/
│   │   ├── receipts.py          # إدارة الوصولات المالية
│   │   ├── sponsors.py          # إدارة الكفلاء
│   │   └── beneficiaries.py     # إدارة المستفيدين
│   ├── templates/
│   │   └── admin_panel/
│   │       ├── receipts.html
│   │       └── receipt_pdf.html # قالب السند المالي
│   └── urls.py
│
├── sponsor/                     # تطبيق الكافل
│   ├── models.py                # SponsorProfile, PaymentReceipt
│   ├── views.py                 # wallet, download_receipt_pdf
│   └── templates/
│
├── beneficiary/                 # تطبيق المستفيدين
│   ├── models.py                # OrphanForm, FamilyForm, SpecialNeedsForm
│   └── views.py
│
├── logs/
│   └── ruhamaa.log              # سجل الأحداث
│
├── static/                      # الملفات الثابتة
├── media/                       # الملفات المرفوعة
├── locale/                      # ملفات الترجمة (ar/en)
├── manage.py
└── requirements.txt
```

---

## 📦 المتطلبات

```txt
Django>=4.0
mysqlclient
WeasyPrint
openpyxl
Pillow
django-crispy-forms
python-dotenv
```

---

## 🚀 التثبيت والتشغيل

### 1. استنساخ المشروع

```bash
git clone https://github.com/AlaaAlhoot/ruhamaa.git
cd ruhamaa
```

### 2. إنشاء البيئة الافتراضية

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate
```

### 3. تثبيت المتطلبات

```bash
pip install -r requirements.txt
```

### 4. إعداد ملف البيئة

أنشئ ملف `.env` في جذر المشروع:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=ruhamaa_db
DB_USER=root
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=3306

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=منصة رُحَمَاء <your-email@gmail.com>
```

### 5. إعداد قاعدة البيانات

```bash
# إنشاء قاعدة البيانات في MySQL
mysql -u root -p
CREATE DATABASE ruhamaa_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit;

# تطبيق الـ migrations
python manage.py makemigrations
python manage.py migrate
```

### 6. إنشاء مستخدم مدير

```bash
python manage.py createsuperuser
```

### 7. تشغيل السيرفر

```bash
python manage.py runserver
```

افتح المتصفح على: `http://127.0.0.1:8000`

---

### 🖥️ النشر على الخادم (Production)

```bash
# جمع الملفات الثابتة
python manage.py collectstatic

# تشغيل Gunicorn
gunicorn ruhamaa.wsgi:application --bind 0.0.0.0:8000 --workers 3

# إعداد Nginx (nginx.conf)
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ { root /path/to/ruhamaa; }
    location /media/  { root /path/to/ruhamaa; }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 👤 المستخدمون والصلاحيات

| النوع | الوصف | الصلاحيات |
|-------|-------|-----------|
| **مدير النظام** | Admin Panel كامل | مراجعة الوصولات، إدارة المستفيدين، التقارير، الإعدادات |
| **الكافل** | Sponsor Dashboard | رفع الوصولات، تتبع الحالة، تحميل السندات، إعادة الإرسال |
| **المستفيد** | Beneficiary Profile | عرض بيانات الكفالة |

---

## 🔐 الميزات الأمنية

- حماية CSRF على جميع النماذج
- Decorators مخصصة `@admin_required` و `@sponsor_required`
- سجل نشاط كامل لجميع العمليات الحساسة
- علامات مائية أمنية على السندات المالية لمنع التزوير
- التحقق من صحة جميع المدخلات في الـ Backend
- وضع الصيانة مع صفحة مخصصة

---

## 📊 نموذج البيانات الرئيسي

```
CustomUser (المستخدم)
    ├── SponsorProfile (الكافل)
    │       └── PaymentReceipt (الوصل المالي)
    │               ├── amount_original, currency
    │               ├── amount_shekel, amount_dollar
    │               ├── status: بانتظار المراجعة / موافق / مرفوض
    │               └── receipt_image
    │
    ├── OrphanForm (اليتيم)
    ├── FamilyForm (الأسرة)
    └── SpecialNeedsForm (ذوو الاحتياجات الخاصة)

Payment (سجل الدفعات)
Notification (الإشعارات)
SystemSettings (إعدادات الموقع)
```

---

## 🤝 المساهمة

المساهمات مرحب بها! يرجى اتباع الخطوات التالية:

1. Fork المشروع
2. أنشئ branch جديد: `git checkout -b feature/اسم-الميزة`
3. Commit التغييرات: `git commit -m 'إضافة ميزة جديدة'`
4. Push: `git push origin feature/اسم-الميزة`
5. افتح Pull Request

---

## 👨‍💻 المطور

<div align="center">

**علاء عماد الحوت**
*Alaa Emad Al-Hout*

مطور Django متكامل — مدرس جامعي — باحث في تكنولوجيا المعلومات

[![GitHub](https://img.shields.io/badge/GitHub-AlaaAlhoot-181717?style=for-the-badge&logo=github)](https://github.com/AlaaAlhoot)

*الجامعة الإسلامية بغزة — قسم تكنولوجيا المعلومات*

</div>

---

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT — انظر ملف [LICENSE](LICENSE) للتفاصيل.

---

<div align="center">

صُنع بـ ❤️ لخدمة أهل غزة — جمعية نسائم فلسطين الخيرية 🇵🇸

</div>
