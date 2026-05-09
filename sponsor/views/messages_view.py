"""
sponsor/views/messages_view.py
"""
import re
import os
from functools import wraps
from django.db.models import Max
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q
from django.utils import timezone

from core.models import CustomUser, Notification, DirectMessage
from sponsor.models import SponsorProfile
from core.utils import log_activity, create_notification, fmt_dt


def sponsor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if request.user.user_type != 'sponsor':
            return redirect('/login/')
        if not request.user.is_approved:
            return render(request, 'sponsor/pending.html')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_profile(user):
    try:
        return user.sponsor_profile
    except Exception:
        profile, _ = SponsorProfile.objects.get_or_create(user=user)
        return profile


# ══════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════
@sponsor_required
def messages_view(request):
    user    = request.user
    profile = _get_profile(user)

    # ══ جلب الأدمن بثلاث طرق ══
    admin = CustomUser.objects.filter(
        user_type='admin', is_active=True,
        sent_direct_messages__recipient=user
    ).first()

    if not admin:
        admin = CustomUser.objects.filter(
            user_type='admin', is_active=True, is_staff=True,
        ).first()

    if not admin:
        admin = CustomUser.objects.filter(
            user_type='admin', is_active=True,
        ).order_by('-date_joined').first()

    # رسائل مع الأدمن
    admin_messages = DirectMessage.objects.filter(
        Q(sender=user, recipient__user_type='admin') |
        Q(sender__user_type='admin', recipient=user)
    ).order_by('created_at')

    # تحديث مقروءة
    DirectMessage.objects.filter(
        sender__user_type='admin', recipient=user, is_read=False
    ).update(is_read=True, is_delivered=True)

    # محادثات المستفيدين
    bene_chats = []
    if profile.can_contact:
        from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
        for f in (
            list(OrphanForm.objects.filter(sponsor=profile).select_related('user')) +
            list(SpecialNeedsForm.objects.filter(sponsor=profile).select_related('user')) +
            list(FamilyForm.objects.filter(sponsor=profile).select_related('user'))
        ):
            if f.user.allow_direct_comm:
                msgs = DirectMessage.objects.filter(
                    Q(sender=user, recipient=f.user) |
                    Q(sender=f.user, recipient=user)
                ).order_by('created_at')

                DirectMessage.objects.filter(
                    sender=f.user, recipient=user, is_read=False
                ).update(is_read=True, is_delivered=True)

                bene_chats.append({
                    'user':     f.user,
                    'form':     f,
                    'messages': msgs,
                    'unread':   0,  # صفر لأنها تحديث فوري أعلاه
                })

    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()

    # آخر ID للرسائل الواردة — لمنع الـ badge من إحصاء القديمة
    from django.db.models import Max
    last_msg_id = DirectMessage.objects.filter(
        recipient=user
    ).aggregate(m=Max('id'))['m'] or 0

    return render(request, 'sponsor/messages.html', {
        'admin':          admin,
        'admin_messages': admin_messages,
        'bene_chats':     bene_chats,
        'can_contact':    profile.can_contact,
        'notif_count':    notif_count,
        'last_msg_id':    last_msg_id,
    })


# ══════════════════════════════════════════════════════════
# إرسال رسالة
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_POST
@csrf_protect
def send_message(request):
    user         = request.user
    recipient_id = request.POST.get('recipient_id', '').strip()
    message_text = request.POST.get('message', '').strip()

    # XSS
    if message_text and re.search(r'<script|javascript:|onerror=', message_text, re.I):
        return JsonResponse({'status': 'error', 'message': 'مدخل غير صالح'}, status=400)
    if message_text and len(message_text) > 2000:
        return JsonResponse({'status': 'error', 'message': 'الرسالة طويلة جداً'})

    attachment  = request.FILES.get('attachment')
    if not message_text and not attachment:
        return JsonResponse({'status': 'error', 'message': 'الرسالة فارغة'})

    # فحص حجم المرفق
    if attachment and attachment.size > 3 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'حجم الملف يتجاوز 3MB'})

    try:
        recipient = CustomUser.objects.get(pk=recipient_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'المستلم غير موجود'})

    # إنشاء الرسالة
    msg = DirectMessage(
        sender    = user,
        recipient = recipient,
        message   = message_text,
    )
    if attachment:
        msg.attachment = attachment
    msg.save()

    # تحديد كـ delivered
    msg.is_delivered = True
    msg.save(update_fields=['is_delivered'])

    # إشعار
    create_notification(
        recipient  = recipient,
        ntype      = 'NEW_MSG',
        title      = 'رسالة جديدة 💬',
        message    = f'رسالة من {user.get_full_name()}',
        sender     = user,
        action_url = '/sponsor/messages/',
    )

    log_activity(user, 'MESSAGE',
                 description=f'رسالة إلى {recipient.get_full_name()}',
                 request=request)

    # نوع المرفق
    att_url  = msg.attachment.url if msg.attachment else None
    att_type = None
    if msg.attachment:
        ext = os.path.splitext(msg.attachment.name)[1].lower()
        att_type = 'image' if ext in ['.jpg','.jpeg','.png','.gif','.webp','.bmp'] else 'file'

    return JsonResponse({
        'status':     'success',
        'id':         msg.pk,
        'time':       fmt_dt(msg.created_at),
        'attachment': att_url,
        'att_type':   att_type,
    })


# ══════════════════════════════════════════════════════════
# Polling — رسائل جديدة
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_GET
def poll_messages(request):
    user     = request.user
    last_id  = int(request.GET.get('last_id', 0))

    new_msgs = DirectMessage.objects.filter(
        recipient=user,
        id__gt=last_id,
    ).select_related('sender').order_by('id')

    messages = []
    for m in new_msgs:
        att_type = None
        if m.attachment:
            ext = os.path.splitext(m.attachment.name)[1].lower()
            att_type = 'image' if ext in ['.jpg','.jpeg','.png','.gif','.webp'] else 'file'

        messages.append({
            'id':          m.pk,
            'text':        m.message,
            'time':        fmt_dt(m.created_at),
            'sender_id':   m.sender.pk,
            'sender_type': m.sender.user_type,
            'attachment':  m.attachment.url if m.attachment else None,
            'att_type':    att_type,
        })

    # تحديد كـ delivered
    new_msgs.filter(is_delivered=False).update(is_delivered=True)

    return JsonResponse({'messages': messages})


# ══════════════════════════════════════════════════════════
# تحديد مقروءة
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_POST
@csrf_protect
def mark_read(request):
    user      = request.user
    sender_id = request.POST.get('sender_id', '').strip()
    if not sender_id:
        return JsonResponse({'status': 'error'})

    DirectMessage.objects.filter(
        sender_id=sender_id, recipient=user, is_read=False
    ).update(is_read=True)

    return JsonResponse({'status': 'success'})


# ══════════════════════════════════════════════════════════
# حظر مستخدم
# ══════════════════════════════════════════════════════════

@sponsor_required
@require_POST
@csrf_protect
def block_user(request):
    user    = request.user
    user_id = request.POST.get('user_id', '').strip()

    try:
        target = CustomUser.objects.get(pk=user_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'المستخدم غير موجود'})

    # تعطيل allow_direct_comm للمستفيد
    target.allow_direct_comm = False
    target.save(update_fields=['allow_direct_comm'])

    log_activity(user, 'BLOCK',
                 description=f'حظر التواصل مع {target.get_full_name()}',
                 request=request)

    return JsonResponse({'status': 'success', 'message': 'تم الحظر ✅'})
