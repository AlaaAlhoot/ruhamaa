from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect

from core.models import CustomUser, Notification
from core.utils import log_activity
from .decorators import admin_required


@admin_required
def users_list(request):
    user_type = request.GET.get('type', 'all')
    search    = request.GET.get('q', '').strip()

    users = CustomUser.objects.filter(
        is_approved=True
    ).exclude(user_type='admin').order_by('-date_joined')

    if user_type != 'all':
        users = users.filter(user_type=user_type)

    if search:
        users = users.filter(
            first_name__icontains=search
        ) | users.filter(
            family_name__icontains=search
        ) | users.filter(
            id_number__icontains=search
        ) | users.filter(
            email__icontains=search
        )

    notif_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    context = {
        'users':      users.distinct(),
        'user_type':  user_type,
        'search':     search,
        'notif_count':notif_count,
        'counts': {
            'all':     CustomUser.objects.filter(is_approved=True).exclude(user_type='admin').count(),
            'sponsor': CustomUser.objects.filter(is_approved=True, user_type='sponsor').count(),
            'orphan':  CustomUser.objects.filter(is_approved=True, user_type='orphan').count(),
            'family':  CustomUser.objects.filter(is_approved=True, user_type='family').count(),
            'special': CustomUser.objects.filter(is_approved=True, user_type='special').count(),
        }
    }
    return render(request, 'admin_panel/users.html', context)


@admin_required
@require_POST
@csrf_protect
def toggle_user(request):
    """تفعيل / تعطيل المستخدم"""
    user_id = request.POST.get('user_id', '').strip()
    try:
        user = CustomUser.objects.get(pk=user_id)
        user.is_active = not user.is_active
        user.save()

        action = 'تفعيل' if user.is_active else 'تعطيل'
        log_activity(
            request.user, 'UPDATE',
            description = f'{action} حساب: {user.get_full_name()}',
            target_model= 'CustomUser',
            target_id   = user.pk,
            request     = request,
        )
        return JsonResponse({
            'status':    'success',
            'is_active': user.is_active,
            'message':   f'تم {action} الحساب',
        })
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'المستخدم غير موجود'})


@admin_required
@require_POST
@csrf_protect
def delete_user(request):
    user_id = request.POST.get('user_id', '').strip()
    try:
        user = CustomUser.objects.get(pk=user_id)
        name = user.get_full_name()
        user.delete()
        log_activity(
            request.user, 'DELETE',
            description = f'حذف حساب: {name}',
            request     = request,
        )
        return JsonResponse({'status': 'success', 'message': 'تم حذف الحساب'})
    except CustomUser.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'المستخدم غير موجود'})