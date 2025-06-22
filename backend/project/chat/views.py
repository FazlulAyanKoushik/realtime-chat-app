# chat/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from accounts.models import User, UserKind
from chat.models import Thread, Message
from chat.serializers import (
    ThreadSerializer,
    CreateThreadSerializer,
    AssignAdminSerializer,
    MessageSerializer,
)


class ThreadListView(generics.ListAPIView):
    serializer_class = ThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.kind == UserKind.ADMIN:
            return Thread.objects.filter(
                Q(admin=user) | Q(admin=None)
            )
        elif user.kind == UserKind.END_USER:
            return Thread.objects.filter(end_user=user)
        return Thread.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class ThreadCreateView(generics.CreateAPIView):
    serializer_class = CreateThreadSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        thread = serializer.save()

        # Notify admins of new unassigned thread
        from chat.consumers import notify_new_thread
        notify_new_thread(thread)


class AssignAdminView(generics.GenericAPIView):
    serializer_class = AssignAdminSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, thread_uid):
        thread = get_object_or_404(Thread, uid=thread_uid, admin=None)

        # Validate the request
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Assign the admin to the thread
        thread.add_admin(request.user)

        return Response(ThreadSerializer(thread, context={'request': request}).data,
                        status=status.HTTP_200_OK)


class MessageListView(generics.ListAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thread_uid = self.kwargs['thread_uid']
        user = self.request.user

        # Verify the user has access to this thread
        thread = Thread.objects.filter(
            uid=thread_uid
        ).filter(
            Q(end_user=user) | Q(admin=user)
        ).first()

        return thread.messages.select_related('sender').all()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        # Mark messages as read when fetching them
        thread_uid = self.kwargs['thread_uid']

        thread = Thread.objects.filter(
            uid=thread_uid
        ).filter(
            Q(end_user=request.user) | Q(admin=request.user)
        ).first()

        thread.mark_messages_as_read(request.user)

        return response


class MessageCreateView(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        thread_uid = self.kwargs['thread_uid']
        user = self.request.user

        # Verify the user has access to this thread

        thread = Thread.objects.filter(
            uid=thread_uid
        ).filter(
            Q(end_user=user) | Q(admin=user)
        ).first()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = Message.objects.create(
            thread=thread,
            sender=request.user,
            text=serializer.validated_data['text']
        )

        # Notify via WebSocket
        from chat.consumers import send_message_notification
        send_message_notification(message)

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)