from django.urls import path

from admin_panel.views import complaints
from . import views
from admin_panel.views import *
app_name = 'main'

urlpatterns = [
    # ==================== الصفحات الرئيسية ====================
    path('',                  views.home_view,            name='home'),
    path('login/',            views.login_view,           name='login'),
    path('logout/',           views.logout_view,          name='logout'),
    path('register/',         views.register_view,        name='register'),
    path('forgot-password/',  views.forgot_password_view, name='forgot_password'),
    path('contact/',          views.contact_view,         name='contact'),
    path('faq/',              views.faq_view,             name='faq'),
    path('admin-login/',      views.admin_login_view,     name='admin_login'),

    # ==================== API ====================
    path('api/countries/',    views.countries_api,        name='countries_api'),
    path('api/rates/',        views.exchange_rates_api,   name='exchange_rates'),
    path('api/check-unique/', views.check_unique_api,     name='check_unique'),
    path('contact/submit/', complaints.public_submit, name='public_contact'),
]
