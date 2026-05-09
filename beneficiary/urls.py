# ==================== beneficiary/urls.py ====================
from django.urls import path
from beneficiary.views import views, profile,payments,aids,faq_view,beneficiary_notifications_view as nv,reports,dashboard,beneficiary_messages_view

app_name = 'beneficiary'

urlpatterns = [
    # ── صفحة الملف الشخصي ──
    path('profile/', profile.profile_view, name='profile'),
    path('profile/data/', profile.profile_data_api, name='profile_data'),
    path('profile/edit/', profile.profile_edit_api, name='profile_edit'),
    path('profile/check-field/', profile.profile_check_field_api, name='profile_check_field'),
    path('profile/document/upload/', profile.document_upload_api, name='document_upload'),
    path('profile/document/delete/', profile.document_delete_api, name='document_delete'),
    path('profile/export-excel/', profile.export_excel_api, name='profile_export_excel'),
    path('profile/member/save/', profile.member_save_api, name='profile_member_save'),
# في beneficiary/urls.py - داخل urlpatterns
path('profile/export-excel/', profile.export_excel_api, name='profile_export_excel'),

    # ── الصفحات الأصلية (من views.py) ──

# ── المدفوعات ──
path('payments/',                payments.payments_view,        name='payments'),
path('payments/data/',           payments.payments_data_api,    name='payments_data'),
path('payments/detail/',         payments.payment_detail_api,   name='payment_detail'),
path('payments/export-excel/',   payments.export_excel_api,     name='payments_export_excel'),
path('payments/export-pdf/',     payments.export_pdf_api,       name='payments_export_pdf'),
    path('payments/print/', payments.export_pdf_html_api, name='payments_print'),
path('payments/download-pdf/', payments.download_pdf_html_api, name='payments_download_pdf'),
path('aids/',              aids.aids_view,           name='aids'),
path('aids/data/',         aids.aids_data_api,        name='aids_data'),
path('aids/detail/',       aids.aid_detail_api,       name='aid_detail'),
path('aids/export-excel/', aids.export_excel_api,     name='aids_export_excel'),
path('aids/download-pdf/', aids.download_pdf_api,     name='aids_download_pdf'),
path('aids/print/',        aids.export_pdf_html_api,  name='aids_print'),


# في urlpatterns أضف:
path('faq/',       faq_view.faq,      name='faq'),
path('faq/data/',  faq_view.faq_data, name='faq_data'),
 path('notifications/',             nv.notifications,         name='notifications'),
    path('notifications/data/',        nv.notifications_data,    name='notifications_data'),
    path('notifications/read/',        nv.mark_read,             name='notifications_read'),
    path('notifications/read-all/',    nv.mark_all_read,         name='notifications_read_all'),
    path('notifications/delete/',      nv.delete_notification,   name='notifications_delete'),
    path('notifications/delete-read/', nv.delete_all_read,       name='notifications_delete_read'),
    path('notifications/preview/',     nv.notifications_preview, name='notifications_preview'),
# ── التقارير ──
path('reports/',              reports.reports_view,             name='reports'),
path('reports/data/',         reports.reports_data_api,         name='reports_data'),
path('reports/export-excel/', reports.reports_export_excel_api, name='reports_export_excel'),
path('reports/export-pdf/',   reports.reports_export_pdf_api,   name='reports_export_pdf'),
path('reports/export/pdf/', reports.reports_export_html_pdf, name='report_pdf'),
path('reports/download/pdf/', reports.reports_download_pdf, name='report_download_pdf'),

path('messages/',       beneficiary_messages_view.messages_view,  name='messages'),
path('messages/send/',  beneficiary_messages_view.send_message,   name='bene_send_message'),
path('messages/poll/',  beneficiary_messages_view.poll_messages,  name='bene_poll_messages'),
path('messages/read/',  beneficiary_messages_view.mark_read,      name='bene_mark_read'),

    path('notifications/read/',  views.mark_notifications_read,  name='mark_notifications_read'),
    path('dashboard/',dashboard.dashboard_view,name='dashboard'),

    path('api/dashboard-data/',dashboard.dashboard_data_api,name='dashboard_data'),

    path('notifications/read/',dashboard.mark_notifications_read_api,name='mark_notifications_read'),
]