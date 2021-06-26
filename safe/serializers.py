from rest_framework import serializers
from django.contrib.auth.models import Group

from .models import Safe, DoozezUser, Invitation
from .services import InvitationService


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoozezUser
        fields = ['email', 'groups']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']


class SafeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Safe
        fields = ['status', 'name', 'monthly_payment', 'id', 'initiator']


class InvitationReadSerializer(serializers.ModelSerializer):
    recipient = UserSerializer()
    safe = SafeSerializer()
    class Meta:
        model = Invitation
        fields = ['status', 'recipient', 'safe']
        depth = 1


class InvitationUpsertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['status', 'recipient', 'safe']