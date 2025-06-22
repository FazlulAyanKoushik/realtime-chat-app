# chat/serializers.py
from rest_framework import serializers
from accounts.models import User, UserKind
from chat.models import Thread, Message


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('uid', 'email', 'kind')


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ('uid', 'thread', 'sender', 'text', 'read', 'created_at')
        read_only_fields = ('uid', 'created_at', 'sender', 'thread')


class ThreadSerializer(serializers.ModelSerializer):
    end_user = UserSerializer(read_only=True)
    admin = UserSerializer(read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Thread
        fields = ('uid', 'end_user', 'admin', 'last_message',
                  'unread_count', 'created_at', 'updated_at', 'is_active')
        read_only_fields = ('uid', 'created_at', 'updated_at')

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(read=False).exclude(sender=request.user).count()
        return 0


class CreateThreadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Thread
        fields = ('message',)  # Initial message is optional

    def validate(self, data):
        request = self.context.get('request')
        if request and request.user.kind != UserKind.END_USER:
            raise serializers.ValidationError("Only end users can create threads")
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        thread = Thread.objects.create(end_user=request.user)

        # Create initial message if provided
        message_text = validated_data.get('message')
        if message_text:
            Message.objects.create(
                thread=thread,
                sender=request.user,
                text=message_text
            )

        return thread


class AssignAdminSerializer(serializers.Serializer):
    def validate(self, data):
        request = self.context.get('request')
        thread = self.context.get('thread')

        if request and request.user.kind != UserKind.ADMIN:
            raise serializers.ValidationError("Only admins can assign themselves to threads")

        if thread.admin:
            raise serializers.ValidationError("This thread already has an admin assigned")

        return data