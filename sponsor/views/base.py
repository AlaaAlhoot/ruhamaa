from functools import wraps
from django.shortcuts import render, redirect
from sponsor.models import SponsorProfile


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

# views.py
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def notifications_preview(request):
    notifs = request.user.notifications.order_by('-created_at')[:3]
    return JsonResponse({
        'unread_count': notifs.filter(is_read=False).count(),
        'notifications': [{
            'message':  n.message,
            'time':     timesince(n.created_at) + ' مضت',
            'icon':     getattr(n, 'icon', '🔔'),
            'url':      getattr(n, 'url', ''),
            'is_read':  n.is_read,
        } for n in notifs]
    })