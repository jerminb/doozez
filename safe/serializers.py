from rest_framework import serializers
from django.contrib.auth.models import Group

from .models import Safe, DoozezUser, Invitation, ActionPayload


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoozezUser
        fields = ['id', 'email', 'first_name', 'last_name', 'groups']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']


class SafeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Safe
        fields = ['id', 'status', 'name', 'monthly_payment', 'id', 'initiator']


class InvitationReadSerializer(serializers.ModelSerializer):
    recipient = UserSerializer()
    safe = SafeSerializer()

    class Meta:
        model = Invitation
        fields = ['id', 'status', 'recipient', 'safe']


class InvitationUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['status', 'recipient', 'safe']


class ActionPayloadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionPayload
        fields = '__all__'
