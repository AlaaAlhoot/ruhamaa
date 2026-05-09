from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .sponsored_view import sponsor_required
from core.models import Notification
from core.utils import fmt_dt

PREVIEW_LIMIT = 3

NTYPE_ICONS = {
    'NEW_MSG':      '💬',
    'RECEIPT_OK':   '✅',
    'RECEIPT_REJ':  '❌',
    'PAYMENT_DUE':  '📅',
    'END_SPONSOR':  '💔',
    'NEW_RECEIPT':  '📩',
    'INFO_REQUEST': '📋',
    'SYSTEM':       '🔔',
}


@require_GET
@sponsor_required
def notifications_preview(request):
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'error': 'AJAX only'}, status=400)

    try:
        notifs = (
            Notification.objects
            .filter(recipient=request.user)
            .only('title', 'message', 'created_at', 'ntype', 'action_url', 'is_read')
            .order_by('-created_at')[:PREVIEW_LIMIT]
        )

        unread_count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()

        return JsonResponse({
            'unread_count': unread_count,
            'notifications': [
                {
                    'message':  (n.title.strip() if n.title and n.title.strip() else n.message),
                    'time':     fmt_dt(n.created_at),
                    'icon':     NTYPE_ICONS.get(n.ntype, '🔔'),
                    'url':      n.action_url or '',
                    'is_read':  n.is_read,
                }
                for n in notifs
            ],
        })

    except Exception:
        return JsonResponse({'error': 'حدث خطأ أثناء جلب الإشعارات'}, status=500)
