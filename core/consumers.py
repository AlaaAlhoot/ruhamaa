import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):

    # ==================== الاتصال ====================

    async def connect(self):
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.user       = self.scope['user']
        self.group_name = f'notif_{self.user.pk}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

        # إرسال عدد الإشعارات غير المقروءة فور الاتصال
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type':  'unread_count',
            'count': count,
        }))

    # ==================== قطع الاتصال ====================

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # ==================== استقبال رسائل من العميل ====================

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type', '')

        if msg_type == 'mark_read':
            await self.mark_all_read()
            await self.send(text_data=json.dumps({
                'type':  'marked_read',
                'count': 0,
            }))

        elif msg_type == 'mark_one_read':
            notif_id = data.get('id')
            if notif_id:
                await self.mark_one_read(notif_id)
                count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type':  'unread_count',
                    'count': count,
                }))

        elif msg_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))

    # ==================== إرسال إشعار من السيرفر ====================

    async def send_notification(self, event):
        """يُستدعى من channel layer عند إرسال إشعار جديد"""
        await self.send(text_data=json.dumps({
            'type':    'notification',
            'title':   event.get('title',   ''),
            'message': event.get('message', ''),
            'ntype':   event.get('ntype',   ''),
            'url':     event.get('url',     ''),
            'id':      event.get('id',      None),
        }))

        # تحديث عداد الإشعارات تلقائياً
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type':  'unread_count',
            'count': count,
        }))

    # ==================== database_sync_to_async ====================

    @database_sync_to_async
    def get_unread_count(self):
        from .models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()

    @database_sync_to_async
    def mark_all_read(self):
        from .models import Notification
        Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def mark_one_read(self, notif_id):
        from .models import Notification
        Notification.objects.filter(
            pk=notif_id,
            recipient=self.user
        ).update(is_read=True)

    @database_sync_to_async
    def get_latest_notifications(self, limit=5):
        from .models import Notification
        return list(
            Notification.objects.filter(
                recipient=self.user
            ).order_by('-created_at')[:limit].values(
                'id', 'title', 'message', 'ntype',
                'action_url', 'is_read', 'created_at'
            )
        )