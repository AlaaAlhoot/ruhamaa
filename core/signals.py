from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def on_user_approved(sender, instance, created, **kwargs):
    """إشعار + بريد عند موافقة الأدمن"""
    if not created and instance.is_approved:
        from .utils import create_notification, send_approval_email
        from .models import Notification
        if not Notification.objects.filter(recipient=instance, ntype='APPROVED').exists():
            create_notification(
                recipient  = instance,
                ntype      = 'APPROVED',
                title      = 'تم قبول حسابك ✅',
                message    = 'تمت الموافقة على حسابك، يمكنك الآن تسجيل الدخول.',
                action_url = '/login/',
            )
            send_approval_email(instance)