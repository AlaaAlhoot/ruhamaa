from django.utils import timezone


class OnlineTrackerMiddleware:
    """تتبع آخر ظهور للمستخدم"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # لا تتدخل في ردود الملفات
        content_type = response.get('Content-Type', '')
        if any(t in content_type for t in ['application/pdf', 'application/vnd', 'application/octet-stream']):
            return response

        if request.user.is_authenticated:
            from .models import CustomUser
            CustomUser.objects.filter(pk=request.user.pk).update(last_seen=timezone.now())

        return response


class AutoLogoutMiddleware:
    """تسجيل خروج تلقائي بعد 30 دقيقة خمول"""
    TIMEOUT = 30 * 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now           = timezone.now().timestamp()
            last_activity = request.session.get('last_activity')
            if last_activity and (now - last_activity) > self.TIMEOUT:
                from django.contrib.auth import logout
                from .utils import log_activity
                log_activity(
                    request.user, 'LOGOUT',
                    description='خروج تلقائي — انتهاء الجلسة',
                    request=request
                )
                logout(request)
            else:
                request.session['last_activity'] = now
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """إضافة headers أمنية"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options']        = 'DENY'
        response['Referrer-Policy']        = 'strict-origin-when-cross-origin'
        return response





from django.shortcuts import render
from django.http import HttpResponse


import logging
logger = logging.getLogger(__name__)

class MaintenanceMiddleware:
    ALLOWED_PATHS = [
        '/admin-panel/login/',
        '/admin-panel/logout/',
        '/admin/',
        '/static/',
        '/media/',
        '/contact/submit/',
        '/admin-login/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            from core.models import SystemSettings
            val = SystemSettings.get('maintenance_mode', 'false')

            if val != 'true':
                return self.get_response(request)

            for path in self.ALLOWED_PATHS:
                if request.path.startswith(path):
                    return self.get_response(request)

            if request.user.is_authenticated:
                user_type = getattr(request.user, 'user_type', '')
                if user_type == 'admin':
                    return self.get_response(request)
                else:
                    return self._maintenance_response(request)
            else:
                return self._maintenance_response(request)

        except Exception as e:
            logger.error(f"[MAINTENANCE] ERROR: {e}")

        return self.get_response(request)

    def _maintenance_response(self, request):
        from django.shortcuts import render
        from django.middleware.csrf import get_token
        get_token(request)
        try:
            from core.models import SystemSettings
            sys_s = type('S', (), {
                'site_name':     SystemSettings.get('site_name',     'منصة رُحَمَاء'),
                'site_phone':    SystemSettings.get('site_phone',    ''),
                'site_whatsapp': SystemSettings.get('site_whatsapp', ''),
                'site_email':    SystemSettings.get('site_email',    ''),
                'working_hours': SystemSettings.get('working_hours', ''),
            })()
        except Exception:
            sys_s = None
        return render(request, 'main/maintenance.html', {'settings': sys_s}, status=503)




