"""
admin_panel/views/faq_view.py
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from core.models import FAQ, Notification
from .decorators import admin_required


@admin_required
def faq_list(request):
    return render(request, 'admin_panel/faq.html', {
        'notif_count': Notification.objects.filter(recipient=request.user, is_read=False).count(),
    })


@admin_required
@require_GET
def faq_data(request):
    q      = request.GET.get('q',      '').strip()
    target = request.GET.get('target', '')
    status = request.GET.get('status', '')

    qs = FAQ.objects.select_related('created_by').order_by('order', 'created_at')
    if q:      qs = qs.filter(question__icontains=q) | qs.filter(answer__icontains=q)
    if target: qs = qs.filter(target=target)
    if status == 'active':   qs = qs.filter(is_active=True)
    if status == 'inactive': qs = qs.filter(is_active=False)

    TARGET_MAP = {'all':'الجميع','sponsor':'الكفلاء','orphan':'الأيتام'}
    items = [{
        'id':         f.pk,
        'question':   f.question,
        'answer':     f.answer,
        'target':     f.target,
        'target_ar':  TARGET_MAP.get(f.target, f.target),
        'order':      f.order,
        'is_active':  f.is_active,
        'created_by': f.created_by.get_full_name() if f.created_by else '—',
        'created_at': f.created_at.strftime('%Y/%m/%d'),
    } for f in qs.distinct()]

    return JsonResponse({'items': items, 'total': len(items)})


@admin_required
@require_POST
@csrf_protect
def faq_save(request):
    fid      = request.POST.get('id', '').strip()
    question = request.POST.get('question', '').strip()
    answer   = request.POST.get('answer',   '').strip()
    target   = request.POST.get('target',   'all').strip()
    order    = int(request.POST.get('order', 0) or 0)
    is_active= request.POST.get('is_active','1') == '1'

    if not question or not answer:
        return JsonResponse({'status':'error','message':'السؤال والجواب مطلوبان'})

    if fid:
        try:
            f = FAQ.objects.get(pk=fid)
            f.question=question; f.answer=answer; f.target=target
            f.order=order; f.is_active=is_active; f.save()
            return JsonResponse({'status':'success','message':'تم التعديل ✅'})
        except FAQ.DoesNotExist:
            return JsonResponse({'status':'error','message':'السؤال غير موجود'})
    else:
        FAQ.objects.create(
            question=question, answer=answer, target=target,
            order=order, is_active=is_active, created_by=request.user,
        )
        return JsonResponse({'status':'success','message':'تمت الإضافة ✅'})


@admin_required
@require_POST
@csrf_protect
def faq_delete(request):
    fid = request.POST.get('id','').strip()
    try:
        FAQ.objects.get(pk=fid).delete()
        return JsonResponse({'status':'success','message':'تم الحذف ✅'})
    except FAQ.DoesNotExist:
        return JsonResponse({'status':'error','message':'السؤال غير موجود'})
