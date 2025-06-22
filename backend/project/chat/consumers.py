# chat/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

from accounts.models import UserKind
from chat.models import Thread, Message
from chat.serializers import ThreadSerializer, MessageSerializer

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
        else:
            # Join user's personal channel
            self.user_channel = f"user_{self.user.uid}"
            await self.channel_layer.group_add(self.user_channel, self.channel_name)

            # Join admin channel if user is admin
            if self.user.kind == UserKind.ADMIN:
                await self.channel_layer.group_add("admins", self.channel_name)

            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'user_channel'):
            await self.channel_layer.group_discard(self.user_channel, self.channel_name)
        if hasattr(self, 'user') and self.user.kind == UserKind.ADMIN:
            await self.channel_layer.group_discard("admins", self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        if message_type == 'read_messages':
            thread_uid = text_data_json.get('thread_uid')
            await self.mark_messages_as_read(thread_uid)

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))

    async def chat_notification(self, event):
        notification = event['notification']
        await self.send(text_data=json.dumps(notification))

    @database_sync_to_async
    def mark_messages_as_read(self, thread_uid):
        thread = Thread.objects.filter(uid=thread_uid).first()
        if thread:
            thread.mark_messages_as_read(self.user)


def send_message_notification(message):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    serializer = MessageSerializer(message)

    # Send to sender
    async_to_sync(channel_layer.group_send)(
        f"user_{message.sender.uid}",
        {
            "type": "chat.message",
            "message": {
                "type": "message_sent",
                "data": serializer.data
            }
        }
    )

    # Send to receiver
    if message.thread.admin:
        receiver = message.thread.admin if message.sender == message.thread.end_user else message.thread.end_user
        async_to_sync(channel_layer.group_send)(
            f"user_{receiver.uid}",
            {
                "type": "chat.message",
                "message": {
                    "type": "message_received",
                    "data": serializer.data
                }
            }
        )


def notify_new_thread(thread):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    serializer = ThreadSerializer(thread)

    # Notify all admins
    async_to_sync(channel_layer.group_send)(
        "admins",
        {
            "type": "chat.notification",
            "notification": {
                "type": "new_thread",
                "data": serializer.data
            }
        }
    )


def notify_admin_assigned(thread):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    serializer = ThreadSerializer(thread)

    # Notify the end user
    async_to_sync(channel_layer.group_send)(
        f"user_{thread.end_user.uid}",
        {
            "type": "chat.notification",
            "notification": {
                "type": "admin_assigned",
                "data": serializer.data
            }
        }
    )