"""
sponsor/views/faq_view.py
صفحة الأسئلة الشائعة — لوحة الكافل
"""
from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from core.models import FAQ, Notification


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


@sponsor_required
def faq(request):
    user        = request.user
    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()
    return render(request, 'sponsor/faq.html', {
        'notif_count': notif_count,
    })


@sponsor_required
@require_GET
def faq_data(request):
    q = request.GET.get('q', '').strip()

    qs = FAQ.objects.filter(
        is_active=True,
        target__in=['all', 'sponsor']
    ).order_by('order', 'created_at')

    if q:
        qs = qs.filter(question__icontains=q) | qs.filter(answer__icontains=q)
        qs = qs.distinct()

    items = [{'id': f.pk, 'question': f.question, 'answer': f.answer} for f in qs]
    return JsonResponse({'items': items, 'total': len(items)})
