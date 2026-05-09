"""
beneficiary/views/messages_view.py
"""
import os
import re
from functools import wraps
from django.db.models import Max
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_protect
from django.db.models import Q

from core.models import CustomUser, Notification, DirectMessage
from core.utils import log_activity, create_notification, fmt_dt


def beneficiary_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/login/')
        if request.user.user_type not in ('orphan', 'family', 'special'):
            return redirect('/login/')
        if not request.user.is_approved:
            return render(request, 'beneficiary/pending.html')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_admin():
    """جلب الأدمن المناسب بثلاث طرق fallback"""
    admin = CustomUser.objects.filter(user_type='admin', is_active=True, is_staff=True).first()
    if not admin:
        admin = CustomUser.objects.filter(user_type='admin', is_active=True).order_by('-date_joined').first()
    return admin


def _get_sponsor(user):
    """جلب الكافل المرتبط بالمستفيد"""
    from beneficiary.models import OrphanForm, SpecialNeedsForm, FamilyForm
    model_map = {
        'orphan':  OrphanForm,
        'family':  FamilyForm,
        'special': SpecialNeedsForm,
    }
    Model = model_map.get(user.user_type)
    if not Model:
        return None
    try:
        form = Model.objects.select_related('sponsor__user').get(user=user)
        if hasattr(form, 'sponsor') and form.sponsor:
            return form.sponsor.user
    except Model.DoesNotExist:
        pass
    return None


# ══════════════════════════════════════════════════════════
# الصفحة الرئيسية
# ══════════════════════════════════════════════════════════

@beneficiary_required
def messages_view(request):
    user  = request.user
    admin = _get_admin()

    # رسائل مع الأدمن
    admin_messages = DirectMessage.objects.filter(
        Q(sender=user, recipient__user_type='admin') |
        Q(sender__user_type='admin', recipient=user)
    ).order_by('created_at')

    # رسائل مع الكافل
    sponsor          = None
    sponsor_messages = []
    can_contact      = user.allow_direct_comm

    if can_contact:
        sponsor = _get_sponsor(user)
        if sponsor:
            sponsor_messages = DirectMessage.objects.filter(
                Q(sender=user, recipient=sponsor) |
                Q(sender=sponsor, recipient=user)
            ).order_by('created_at')

    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()

    from django.db.models import Max
    last_msg_id = DirectMessage.objects.filter(
        recipient=user
    ).aggregate(m=Max('id'))['m'] or 0

    return render(request, 'beneficiary/messages.html', {
        'admin':            admin,
        'admin_messages':   admin_messages,
        'sponsor':          sponsor,
        'sponsor_messages': sponsor_messages,
        'can_contact':      can_contact,
        'notif_count':      notif_count,
        'last_msg_id':      last_msg_id,
    })


# ══════════════════════════════════════════════════════════
# إرسال رسالة
# ══════════════════════════════════════════════════════════

@beneficiary_required
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

    attachment = request.FILES.get('attachment')
    if not message_text and not attachment:
        return JsonResponse({'status': 'error', 'message': 'الرسالة فارغة'})
    if attachment and attachment.size > 3 * 1024 * 1024:
        return JsonResponse({'status': 'error', 'message': 'حجم الملف يتجاوز 3MB'})

    try:
        recipient = CustomUser.objects.get(pk=recipient_id)
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'المستلم غير موجود'})

    # التحقق من الصلاحية: المستفيد يرسل فقط للأدمن أو لكافله (لو allow_direct_comm)
    if recipient.user_type == 'admin':
        pass  # مسموح دائماً
    elif recipient.user_type == 'sponsor':
        if not user.allow_direct_comm:
            return JsonResponse({'status': 'error', 'message': 'غير مسموح بالتواصل المباشر'})
        # تأكد أنه كافله هو
        sponsor = _get_sponsor(user)
        if not sponsor or sponsor.pk != recipient.pk:
            return JsonResponse({'status': 'error', 'message': 'غير مسموح'})
    else:
        return JsonResponse({'status': 'error', 'message': 'غير مسموح'})

    msg = DirectMessage(sender=user, recipient=recipient, message=message_text, is_delivered=True)
    if attachment:
        msg.attachment = attachment
    msg.save()

    # تحديد action_url بناءً على نوع المستلم
    action_url = '/sponsor/messages/' if recipient.user_type == 'sponsor' else '/admin-panel/messages/'

    create_notification(
        recipient  = recipient,
        ntype      = 'NEW_MSG',
        title      = 'رسالة جديدة 💬',
        message    = f'رسالة من {user.get_full_name()}',
        sender     = user,
        action_url = action_url,
    )

    log_activity(user, 'MESSAGE',
                 description=f'رسالة إلى {recipient.get_full_name()}',
                 request=request)

    att_url  = msg.attachment.url if msg.attachment else None
    att_type = None
    if msg.attachment:
        ext      = os.path.splitext(msg.attachment.name)[1].lower()
        att_type = 'image' if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'] else 'file'

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

@beneficiary_required
@require_GET
def poll_messages(request):
    user    = request.user
    last_id = int(request.GET.get('last_id', 0))

    new_msgs = DirectMessage.objects.filter(
        recipient=user,
        id__gt=last_id,
    ).select_related('sender').order_by('id')

    messages = []
    for m in new_msgs:
        att_type = None
        if m.attachment:
            ext      = os.path.splitext(m.attachment.name)[1].lower()
            att_type = 'image' if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'] else 'file'

        messages.append({
            'id':          m.pk,
            'text':        m.message,
            'time':        fmt_dt(m.created_at),
            'sender_id':   m.sender.pk,
            'sender_type': m.sender.user_type,
            'attachment':  m.attachment.url if m.attachment else None,
            'att_type':    att_type,
        })

    new_msgs.filter(is_delivered=False).update(is_delivered=True)

    return JsonResponse({'messages': messages})


# ══════════════════════════════════════════════════════════
# تحديد مقروءة
# ══════════════════════════════════════════════════════════

@beneficiary_required
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
