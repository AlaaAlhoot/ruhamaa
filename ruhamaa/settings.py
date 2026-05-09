from decouple import config
from pathlib import Path

# ==================== المسارات الأساسية ====================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==================== الأمان ====================
SECRET_KEY = config('SECRET_KEY')
DEBUG      = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*']

# ==================== التطبيقات ====================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # تطبيقات المشروع
    'core',
    'main',
    'admin_panel',
    'sponsor',
    'beneficiary',

    # مكتبات خارجية
    'channels',
    'rest_framework',
]

# ==================== Middleware ====================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # middleware مخصص
    'core.middleware.MaintenanceMiddleware',
    'core.middleware.OnlineTrackerMiddleware',
    'core.middleware.AutoLogoutMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF = 'ruhamaa.urls'

# ==================== Templates ====================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.global_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ruhamaa.wsgi.application'
ASGI_APPLICATION  = 'ruhamaa.asgi.application'

# ==================== قاعدة البيانات ====================
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     config('DB_NAME'),
        'USER':     config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST':     config('DB_HOST', default='localhost'),
        'PORT':     config('DB_PORT', default='3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# ==================== المستخدم المخصص ====================
AUTH_USER_MODEL = 'core.CustomUser'

# ==================== كلمة المرور ====================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ==================== اللغة والتوقيت ====================
LANGUAGE_CODE = 'ar'
TIME_ZONE     = 'Asia/Gaza'
USE_I18N      = True
USE_L10N      = True
USE_TZ        = True

# ==================== الملفات الثابتة والوسائط ====================
STATIC_URL       = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT      = BASE_DIR / 'staticfiles'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================== البريد الإلكتروني (Brevo SMTP) ====================
EMAIL_BACKEND       = config('EMAIL_BACKEND',
                             default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST          = config('EMAIL_HOST',     default='smtp-relay.brevo.com')
EMAIL_PORT          = config('EMAIL_PORT',     default=587, cast=int)
EMAIL_USE_TLS       = True
EMAIL_HOST_USER     = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL  = config('DEFAULT_FROM_EMAIL')

# ==================== WebSocket (Django Channels) ====================
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# ==================== الجلسات ====================
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE              = 5 * 60  # 300 ثانية
SESSION_COOKIE_SECURE           = not DEBUG
SESSION_COOKIE_HTTPONLY         = True
SESSION_COOKIE_SAMESITE         = 'Lax'

# ==================== الأمان ====================
CSRF_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS      = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# ==================== الكاش ====================
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ==================== REST Framework ====================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ==================== رفع الملفات ====================
FILE_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 4 * 1024 * 1024

# ==================== السجلات (Logging) ====================
import os
import logging

LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {module}: {message}',
            'style':  '{',
        },
    },
    'handlers': {
        'file': {
            'level':     'ERROR',
            'class':     'logging.FileHandler',
            'filename':  str(LOGS_DIR / 'ruhamaa.log'),
            'formatter': 'verbose',
            'encoding':  'utf-8',
        },
        'console': {
            'level':     'DEBUG' if DEBUG else 'ERROR',
            'class':     'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level':    'ERROR',
    },
    'loggers': {
        'django': {
            'handlers':  ['file'],
            'level':     'ERROR',
            'propagate': False,
        },
        # ── إخفاء مخرجات weasyprint و fontTools ──
        'weasyprint': {
            'handlers':  ['file'],
            'level':     'ERROR',
            'propagate': False,
        },
        'fontTools': {
            'handlers':  ['file'],
            'level':     'ERROR',
            'propagate': False,
        },
        'fontTools.ttLib': {
            'handlers':  ['file'],
            'level':     'ERROR',
            'propagate': False,
        },
        'fontTools.subset': {
            'handlers':  ['file'],
            'level':     'ERROR',
            'propagate': False,
        },
    },
}

# تطبيق الإعدادات فوراً على مستوى Python logging
logging.getLogger('weasyprint').setLevel(logging.ERROR)
logging.getLogger('fontTools').setLevel(logging.ERROR)
logging.getLogger('fontTools.ttLib').setLevel(logging.ERROR)
logging.getLogger('fontTools.subset').setLevel(logging.ERROR)