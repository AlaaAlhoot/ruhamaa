"""
beneficiary/views/faq_view.py
صفحة الأسئلة الشائعة — لوحة المستفيد
"""
from functools import wraps
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from core.models import FAQ, Notification
from django.contrib.auth.decorators import login_required




@login_required
def faq(request):
    user        = request.user
    notif_count = Notification.objects.filter(recipient=user, is_read=False).count()
    return render(request, 'beneficiary/faq.html', {
        'notif_count': notif_count,
    })


from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from core.models import FAQ

@login_required
@require_GET
def faq_data(request):
    q = request.GET.get('q', '').strip()

    qs = FAQ.objects.filter(
        is_active=True
    ).exclude(
        target='sponsor'
    ).order_by('order', 'created_at')

    if q:
        qs = (
            qs.filter(question__icontains=q) |
            qs.filter(answer__icontains=q)
        ).distinct()

    items = [
        {
            'id':       f.pk,
            'question': f.question,
            'answer':   f.answer,
            'target':   f.target,
        }
        for f in qs
    ]

    return JsonResponse({
        'items': items,
        'total': len(items)
    })