from django.urls import path
from admin_panel.views import (
    dashboard, requests, users,
    beneficiaries, sponsors, receipts,
    complaints, logs,reports,search,compare,alerts,sponsor_report, map_timeline,faq_view
)
from admin_panel.views import settings as sv
from admin_panel.views import admin_messages_view as adm_msg
app_name = 'admin_panel'

urlpatterns = [

    # ── Dashboard ──
    path('dashboard/',                        dashboard.dashboard,                  name='dashboard'),

path('dashboard/stats/', dashboard.dashboard_stats_api, name='dashboard_stats'),

    # ── طلبات التسجيل ──
    path('requests/',                         requests.requests_list,               name='requests'),
    path('requests/data/',                    requests.requests_data,               name='requests_data'),
    path('requests/approve/',                 requests.approve_user,                name='approve_user'),
    path('requests/reject/',                  requests.reject_user,                 name='reject_user'),
    path('requests/send-message/',            requests.send_message,                name='send_message'),
    path('requests/add-note/',                requests.add_note,                    name='add_note'),
    path('requests/export/',                  requests.export_requests,             name='export_requests'),
    path('requests/export-word/',             requests.export_word,                 name='export_word'),
    path('requests/export-pdf/',              requests.export_pdf,                  name='export_pdf'),
    path('requests/print/',                   requests.print_request,               name='print_request'),
    path('requests/count/',                   requests.requests_count,              name='requests_count'),
path('sponsors/comm-all/', sponsors.toggle_comm_all, name='toggle_comm_all'),

    # ── المستخدمون ──
    path('users/',                            users.users_list,                     name='users'),
    path('users/toggle/',                     users.toggle_user,                    name='toggle_user'),
    path('users/delete/',                     users.delete_user,                    name='delete_user'),

    # ── الأيتام ──
    path('orphans/',                          beneficiaries.orphans_list,           name='orphans'),

    # ── الأسر ──
    path('families/',                         beneficiaries.families_list,          name='families'),

    # ── ذوو الاحتياجات ──
    path('specials/',                         beneficiaries.specials_list,          name='specials'),

    # ── API المستفيدين الموحّد ──
    path('beneficiaries/data/',               beneficiaries.beneficiaries_data,     name='beneficiaries_data'),
    path('beneficiaries/detail/',             beneficiaries.beneficiary_detail,     name='beneficiary_detail'),
    path('beneficiaries/toggle/',             beneficiaries.toggle_user,            name='toggle_bene'),
    path('beneficiaries/delete/',             beneficiaries.delete_user,            name='delete_bene'),
    path('beneficiaries/status/',             beneficiaries.update_status,          name='update_bene_status'),
    path('beneficiaries/export/',             beneficiaries.export_beneficiaries,   name='export_beneficiaries'),
    path('beneficiaries/comm/',               beneficiaries.toggle_comm,            name='toggle_comm'),
    path('beneficiaries/sponsor/change/',     beneficiaries.change_sponsor,         name='change_sponsor'),
    path('beneficiaries/sponsor/remove/',     beneficiaries.remove_sponsor,         name='remove_sponsor'),


path('receipts/',                  receipts.receipts_list,        name='receipts'),
path('receipts/data/',             receipts.receipts_data,        name='receipts_data'),
path('receipts/detail/',           receipts.receipt_detail,       name='receipt_detail'),
path('receipts/approve/',          receipts.approve_receipt,      name='receipt_approve'),
path('receipts/reject/',           receipts.reject_receipt,       name='receipt_reject'),
path('receipts/delete/',           receipts.delete_receipt,       name='receipt_delete'),
path('receipts/export/',           receipts.export_receipts,      name='receipt_export'),
path('receipts/pdf/',              receipts.receipt_pdf,          name='receipt_pdf'),
path('receipts/beneficiaries/',    receipts.sponsor_beneficiaries,name='receipt_beneficiaries'),
    # الملاحظات
    path('beneficiaries/notes/',              beneficiaries.get_notes,              name='get_notes'),
    path('beneficiaries/notes/add/',          beneficiaries.add_note,               name='add_bene_note'),

    # المدفوعات
    path('beneficiaries/payments/',           beneficiaries.get_payments,           name='get_payments'),
    path('beneficiaries/payments/add/',       beneficiaries.add_payment,            name='add_payment'),
    path('beneficiaries/payments/delete/',    beneficiaries.delete_payment,         name='delete_payment'),
    path('beneficiaries/payments/export/',    beneficiaries.export_payments,        name='export_payments'),

    # المساعدات
    path('beneficiaries/aids/',               beneficiaries.get_aids,               name='get_aids'),
    path('beneficiaries/aids/add/',           beneficiaries.add_aid,                name='add_aid'),
    path('beneficiaries/aids/delete/',        beneficiaries.delete_aid,             name='delete_aid'),

    # سجل النشاط
    path('beneficiaries/logs/',               beneficiaries.get_logs,               name='get_bene_logs'),
    path('beneficiaries/logs/export/',        beneficiaries.export_logs,            name='export_bene_logs'),

    # ── الكفلاء ──
    path('sponsors/',                         sponsors.sponsors_list,               name='sponsors'),
    path('sponsors/contact/',                 sponsors.toggle_contact,              name='toggle_contact'),

    # ── الوصولات المالية ──


    # ── الشكاوى ──
path('complaints/',          complaints.complaints_list,   name='complaints'),
path('complaints/data/',     complaints.complaints_data,   name='complaints_data'),
path('complaints/detail/',   complaints.complaint_detail,  name='complaint_detail'),
path('complaints/seen/',     complaints.mark_seen,         name='complaint_seen'),
path('complaints/reply/',    complaints.reply_complaint,   name='complaint_reply'),
path('complaints/priority/', complaints.set_priority,      name='complaint_priority'),
path('complaints/note/',     complaints.add_internal_note, name='complaint_note'),
path('complaints/delete/',   complaints.delete_complaint,  name='complaint_delete'),
path('complaints/export/',   complaints.export_complaints, name='complaint_export'),

    # ── سجل النشاط العام ──
    path('logs/', logs.logs_list, name='logs'),
    path('logs/data/', logs.logs_data, name='logs_data'),
    path('logs/detail/', logs.log_detail, name='log_detail'),
    path('logs/delete-old/', logs.delete_old_logs, name='logs_delete_old'),
    path('logs/export/', logs.export_logs, name='export_logs'),

    # ── الإعدادات ──


path('settings/',                       sv.settings_view,           name='settings'),
path('settings/profile/',               sv.update_profile,          name='settings.update_profile'),
path('settings/password/',              sv.change_password,         name='settings.change_password'),
path('settings/check-username/',        sv.check_username,          name='settings.check_username'),
path('settings/check-email/',           sv.check_email_available,   name='settings.check_email'),
path('settings/admin/create/',          sv.create_admin,            name='settings.admin_create'),
path('settings/admin/update/',          sv.update_admin,            name='settings.admin_update'),
path('settings/admin/toggle/',          sv.toggle_admin,            name='settings.admin_toggle'),
path('settings/admin/toggle-settings/', sv.toggle_admin_settings,   name='settings.admin_toggle_settings'),
path('settings/site/',                  sv.update_site_info,        name='settings.update_site_info'),
path('settings/maintenance/',           sv.toggle_maintenance,      name='settings.toggle_maintenance'),
path('settings/rates/',                 sv.get_rates,               name='settings.get_rates'),
path('settings/db-stats/',              sv.db_stats,                name='settings.db_stats'),
path('settings/clear-cache/',           sv.clear_cache,             name='settings.clear_cache'),
path('settings/optimize-db/',           sv.optimize_db,             name='settings.optimize_db'),
path('settings/backup/',                sv.backup_data,             name='settings.backup'),
path('settings/test-email/',            sv.test_email,              name='settings.test_email'),
path('settings/toggle-notifications/', sv.toggle_notifications,    name='settings.toggle_notifications'),
path('settings/security/',              sv.update_security,         name='settings.security'),
path('settings/blocked-ips/',           sv.manage_blocked_ips,      name='settings.blocked_ips'),
path('settings/system-info/',           sv.system_info,             name='settings.system_info'),
# ── الكفلاء ──
    path('sponsors/',                      sponsors.sponsors_list,        name='sponsors'),
    path('sponsors/data/',                 sponsors.sponsors_data,        name='sponsors_data'),
    path('sponsors/detail/',               sponsors.sponsor_detail,       name='sponsor_detail'),
    path('sponsors/toggle/',               sponsors.toggle_sponsor,       name='toggle_sponsor'),
    path('sponsors/delete/',               sponsors.delete_sponsor,       name='delete_sponsor'),
    path('sponsors/notes/',                sponsors.get_sponsor_notes,    name='get_sponsor_notes'),
    path('sponsors/notes/add/',            sponsors.add_sponsor_note,     name='add_sponsor_note'),
    path('sponsors/contact/',              sponsors.toggle_contact,       name='toggle_contact'),
    path('sponsors/logs/',                 sponsors.get_sponsor_logs,     name='get_sponsor_logs'),
    path('sponsors/logs/export/',          sponsors.export_sponsor_logs,  name='export_sponsor_logs'),
    path('sponsors/export/',               sponsors.export_sponsors,      name='export_sponsors'),
    path('beneficiaries/notes/edit/',   beneficiaries.edit_note,    name='edit_note'),
    path('beneficiaries/notes/delete/', beneficiaries.delete_note,  name='delete_note'),
    path('beneficiaries/notes/export/', beneficiaries.export_notes, name='export_notes'),
    path('beneficiaries/aids/edit/',   beneficiaries.edit_aid,   name='edit_aid'),
    path('beneficiaries/aids/export/', beneficiaries.export_aids, name='export_aids'),
    path('beneficiaries/messages/',        beneficiaries.get_messages,    name='get_messages'),
    path('beneficiaries/messages/export/', beneficiaries.export_messages, name='export_messages'),
    path('beneficiaries/export-single/', beneficiaries.export_single_user, name='export_single_user'),


    path('reports/',              reports.reports_view,        name='reports'),
    path('reports/data/',         reports.reports_data,        name='reports_data'),
    path('reports/export-excel/', reports.export_report_excel, name='export_report_excel'),
    path('reports/export-pdf/',   reports.export_report_pdf,   name='export_report_pdf'),

    path('search/',       search.search_view, name='search'),
    path('search/data/',  search.search_data, name='search_data'),


path('compare/',       compare.compare_view, name='compare'),
path('compare/list/',  compare.compare_list, name='compare_list'),
path('compare/data/',  compare.compare_data, name='compare_data'),


path('alerts/',             alerts.alerts_view,         name='alerts'),
path('alerts/data/',        alerts.alerts_data,         name='alerts_data'),
path('alerts/dismiss/',     alerts.dismiss_alert,       name='dismiss_alert'),
path('alerts/dismiss-all/', alerts.dismiss_all_alerts,  name='dismiss_all_alerts'),


path('sponsors/report/send/',         sponsor_report.send_report,     name='send_sponsor_report'),
path('sponsors/report/send-all/',     sponsor_report.send_all_reports, name='send_all_reports'),
path('sponsors/report/history/',      sponsor_report.report_history,  name='report_history'),
path('sponsors/report/view/<int:pk>/',sponsor_report.view_report,     name='view_report'),
path('sponsors/benes/', sponsors.get_benes, name='sponsor_benes'),
path('sponsors/bene-pays/',        sponsors.get_bene_pays,       name='sponsor_bene_pays'),
path('sponsors/bene-pays/export/', sponsors.export_bene_pays,    name='export_bene_pays'),
path('sponsors/pays-export/',      sponsors.export_sponsor_pays, name='export_sponsor_pays'),
path('beneficiaries/edit/', beneficiaries.edit_beneficiary, name='edit_beneficiary'),
path('requests/check-field/', requests.check_field, name='check_field'),
path('sponsors/edit/', sponsors.edit_sponsor, name='edit_sponsor'),


path('map-timeline/',          map_timeline.page,                name='map_timeline'),
path('map-timeline/map-data/', map_timeline.map_data,            name='map_timeline_data'),
path('map-timeline/timeline/', map_timeline.timeline_data,       name='timeline_data'),
path('map-timeline/search/',   map_timeline.search_beneficiaries,name='timeline_search'),
path('settings/admin/delete/', sv.delete_admin, name='settings.admin_delete'),


path('faq/',        faq_view.faq_list,  name='faq'),
path('faq/data/',   faq_view.faq_data,  name='faq_data'),
path('faq/save/',   faq_view.faq_save,  name='faq_save'),
path('faq/delete/', faq_view.faq_delete,name='faq_delete'),


path('messages/',              adm_msg.messages_view,    name='messages'),
path('messages/conversation/', adm_msg.get_conversation, name='messages_conversation'),
path('messages/send/',         adm_msg.send_message,     name='messages_send'),
path('messages/poll/',         adm_msg.poll_messages,    name='messages_poll'),
path('messages/export/',       adm_msg.export_conversation, name='messages_export'),
path('messages/user-convs/', adm_msg.get_user_conversations, name='admin_user_convs'),
path('receipts/pdf-download/', receipts.receipt_pdf_download, name='receipt_pdf_download'),

]