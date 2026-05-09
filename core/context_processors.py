def global_context(request):
    if not request.user.is_authenticated:
        return {'smart_alerts_count': 0, 'unread_messages_count': 0}

    from core.models import DirectMessage
    unread_messages_count = DirectMessage.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    smart_alerts_count = 0
    if request.user.user_type == 'admin':
        from core.models import SmartAlert
        smart_alerts_count = SmartAlert.objects.filter(
            status='active', level__in=['critical', 'high']
        ).count()

    return {
        'smart_alerts_count':    smart_alerts_count,
        'unread_messages_count': unread_messages_count,
    }