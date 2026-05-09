from django.contrib import admin as django_admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # لوحة Django الافتراضية
    path('django-admin/', django_admin.site.urls),

    # التطبيقات
    path('',              include('main.urls')),
    path('admin-panel/',  include('admin_panel.urls')),
    path('sponsor/',      include('sponsor.urls')),
    path('beneficiary/',  include('beneficiary.urls')),
]

# الملفات في بيئة التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)