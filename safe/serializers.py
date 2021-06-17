from rest_framework import serializers
from django.contrib.auth.models import Group

from .models import Safe, DoozezUser


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DoozezUser
        fields = ['url', 'email', 'groups']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class SafeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Safe
        fields = ['url', 'name', 'id']


class InvitationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Safe
        fields = ['url', 'status', 'sender', 'recipient', 'safe']
