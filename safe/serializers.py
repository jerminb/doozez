from rest_framework import serializers
from django.contrib.auth.models import Group

from .models import Safe, DoozezUser, Invitation, ActionPayload, Participation, PaymentMethod
from .fields import NullableJSONField


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
    status = serializers.CharField(source='get_status_display', required=False)

    class Meta:
        model = Invitation
        fields = ['status', 'recipient', 'safe']


class ActionPayloadSerializer(serializers.ModelSerializer):
    json_data = NullableJSONField(required=False, allow_null=True)

    class Meta:
        model = ActionPayload
        fields = ['action', 'json_data']


class ParticipationSerializer(serializers.ModelSerializer):
    user_role = serializers.CharField(source='get_user_role_display')
    status = serializers.CharField(source='get_status_display')
    user = UserSerializer()
    safe = SafeSerializer()

    class Meta:
        model = Participation
        fields = '__all__'


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'is_default']
