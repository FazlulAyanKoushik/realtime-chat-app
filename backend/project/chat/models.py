# chat/models.py
from django.contrib.auth import get_user_model
from django.db import models

from accounts.models import BaseModelWithUID, UserKind

User = get_user_model()


class Thread(BaseModelWithUID):
    """
    Represents a conversation thread between users.
    Initially created with only the end user, then admin joins later.
    """
    end_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='threads_as_end_user'
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='threads_as_admin'
    )
    last_message = models.ForeignKey(
        'Message',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='last_message_thread'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        if self.admin:
            return f"Thread between {self.end_user.email} and {self.admin.email}"
        return f"Thread with {self.end_user.email} (unassigned)"

    def mark_messages_as_read(self, user):
        """
        Mark all unread messages in the thread as read for the given user
        """
        self.messages.filter(sender=user).exclude(read=True).update(read=True)

    def add_admin(self, admin):
        """
        Assign an admin to the thread
        """
        if self.admin:
            raise ValueError("Thread already has an admin assigned")
        if admin.kind != UserKind.ADMIN:
            raise ValueError("Only admins can be assigned to threads")

        self.admin = admin
        self.save()

        # Notify both parties
        from chat.consumers import notify_admin_assigned
        notify_admin_assigned(self)


class Message(BaseModelWithUID):
    """
    Represents a message in a chat thread
    """
    thread = models.ForeignKey(
        Thread,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    text = models.TextField()
    read = models.BooleanField(default=False)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f"Message from {self.sender.email} in {self.thread}"

    def save(self, *args, **kwargs):
        """
        Update thread's last message when saving a new message
        """
        super().save(*args, **kwargs)
        self.thread.last_message = self
        self.thread.save()