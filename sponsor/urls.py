from django.urls import path
from . import views
from sponsor.views import (
    orphans_view, compare, sponsored_view, wallet_view,
    profile_view, notifications_view, reports_view,
    faq_view, messages_view as msg_view,dashboard_view,notifications_preview as nv
)

app_name = 'sponsor'

urlpatterns = [
    path('dashboard/', dashboard_view.dashboard, name='dashboard'),
# urls.py


path('notifications/preview/', nv.notifications_preview, name='notifications_preview'),
    # ── فرص الكفالة ──
    path('free/',              orphans_view.orphans,           name='orphans'),
    path('free/data/',         orphans_view.free_data,         name='free_data'),
    path('free/detail/',       orphans_view.free_detail,       name='free_detail'),
    path('free/sponsor/',      orphans_view.do_sponsor,        name='free_sponsor'),
    path('free/print/',        orphans_view.print_beneficiary, name='free_print'),
    path('free/pdf/',          orphans_view.download_pdf,      name='free_pdf'),
    path('free/info-request/', orphans_view.info_request,      name='free_info_request'),
    path('free/search/',       orphans_view.global_search,     name='free_search'),

    # ── مستفيدوي ──
    path('sponsored/',         sponsored_view.sponsored,              name='sponsored'),
    path('sponsored/data/',    sponsored_view.sponsored_data,         name='sponsored_data'),
    path('sponsored/detail/',  sponsored_view.sponsored_detail,       name='sponsored_detail'),
    path('sponsored/end/',     sponsored_view.end_sponsorship,        name='sponsored_end'),
    path('sponsored/print/',   sponsored_view.print_sponsored,        name='sponsored_print'),
    path('sponsored/pdf/',     sponsored_view.download_sponsored_pdf, name='sponsored_pdf'),
    path('sponsored/export/',  sponsored_view.export_excel,           name='sponsored_export'),

    # ── المحفظة ──
    path('wallet/',                wallet_view.wallet,                name='wallet'),
    path('wallet/data/',           wallet_view.receipts_data,         name='wallet_data'),
    path('wallet/submit/',         wallet_view.submit_receipt,        name='wallet_submit'),
    path('wallet/check-unique/',   wallet_view.check_unique,          name='wallet_check_unique'),
    path('wallet/resubmit/',       wallet_view.resubmit_receipt,      name='wallet_resubmit'),
    path('wallet/export/',         wallet_view.export_receipts_excel, name='wallet_export'),
    path('wallet/receipt-pdf/',    wallet_view.download_receipt_pdf,  name='wallet_receipt_pdf'),

    # ── الملف الشخصي ──
    path('profile/',                 profile_view.profile,              name='profile'),
    path('profile/update/',          profile_view.update_profile,       name='profile_update'),
    path('profile/change-password/', profile_view.change_password,      name='profile_change_password'),
    path('profile/check-email/',     profile_view.check_email,          name='profile_check_email'),
    path('profile/check-phone/',     profile_view.check_phone,          name='profile_check_phone'),
    path('profile/check-id/',        profile_view.check_id_number,      name='profile_check_id'),
    path('profile/export-excel/',    profile_view.export_excel,         name='profile_export_excel'),
    path('profile/export-pdf/',      profile_view.export_pdf,           name='profile_export_pdf'),
    path('profile/export-pdf-blob/', profile_view.export_pdf_blob,      name='profile_export_pdf_blob'),
    path('profile/certificate/',     profile_view.export_certificate,   name='profile_certificate'),
    path('profile/certificate-blob/',profile_view.certificate_blob,     name='profile_certificate_blob'),

    # ── الإشعارات ──
    path('notifications/',             notifications_view.notifications,       name='notifications'),
    path('notifications/data/',        notifications_view.notifications_data,  name='notifications_data'),
    path('notifications/read/',        notifications_view.mark_read,           name='notifications_read'),
    path('notifications/read-all/',    notifications_view.mark_all_read,       name='notifications_read_all'),
    path('notifications/delete/',      notifications_view.delete_notification, name='notifications_delete'),
    path('notifications/delete-read/', notifications_view.delete_all_read,     name='notifications_delete_read'),

    # ── التقارير ──
    path('reports/',                 reports_view.reports,          name='reports'),
    path('reports/data/',            reports_view.reports_data,     name='reports_data'),
    path('reports/export-excel/',    reports_view.export_excel,     name='reports_export_excel'),
    path('reports/export-pdf-blob/', reports_view.export_pdf_blob,  name='reports_export_pdf_blob'),

    # ── الأسئلة الشائعة ──
    path('faq/',       faq_view.faq,       name='faq'),
    path('faq/data/',  faq_view.faq_data,  name='faq_data'),

    # ── التواصل ──
    path('messages/',            msg_view.messages_view, name='messages'),
    path('messages/send/',       msg_view.send_message,  name='messages_send'),
    path('messages/poll/',       msg_view.poll_messages, name='messages_poll'),
    path('messages/mark-read/',  msg_view.mark_read,     name='messages_mark_read'),
    path('messages/block/',      msg_view.block_user,    name='messages_block'),


path('profile/check-id/', profile_view.check_id_number, name='profile_check_id'),
path('compare/',       compare.compare_view, name='compare'),
path('compare/list/',  compare.compare_list, name='compare_list'),
path('compare/data/',  compare.compare_data, name='compare_data'),


path('wallet/',                wallet_view.wallet,                name='wallet'),
path('wallet/data/',           wallet_view.receipts_data,         name='wallet_data'),
path('wallet/submit/',         wallet_view.submit_receipt,        name='wallet_submit'),
path('wallet/check-unique/',   wallet_view.check_unique,          name='wallet_check_unique'),
path('wallet/resubmit/',       wallet_view.resubmit_receipt,      name='wallet_resubmit'),
path('wallet/export/',         wallet_view.export_receipts_excel, name='wallet_export'),
path('wallet/receipt-pdf/',    wallet_view.download_receipt_pdf,  name='wallet_receipt_pdf'),
path('profile/',                profile_view.profile,              name='profile'),
path('profile/update/',         profile_view.update_profile,       name='profile_update'),
path('profile/change-password/',profile_view.change_password,      name='profile_change_password'),
path('profile/check-email/',    profile_view.check_email,          name='profile_check_email'),
path('profile/check-phone/',    profile_view.check_phone,          name='profile_check_phone'),
path('profile/export-excel/',   profile_view.export_excel,         name='profile_export_excel'),
path('profile/export-pdf/',     profile_view.export_pdf,           name='profile_export_pdf'),
path('profile/certificate/',    profile_view.export_certificate,   name='profile_certificate'),


path('reports/',              reports_view.reports,          name='reports'),
path('reports/data/',         reports_view.reports_data,     name='reports_data'),
path('reports/export-excel/', reports_view.export_excel,     name='reports_export_excel'),
path('reports/export-pdf-blob/', reports_view.export_pdf_blob, name='reports_export_pdf_blob'),


path('faq/',       faq_view.faq,      name='faq'),
path('faq/data/',  faq_view.faq_data, name='faq_data'),

    path('receipt/',           views.receipt,          name='receipt'),
    path('receipt/submit/',    views.submit_receipt,   name='submit_receipt'),





]