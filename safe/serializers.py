from django.db.models import Q
from rest_framework import serializers
from django.contrib.auth.models import Group
from rest_auth.registration.serializers import RegisterSerializer

from .models import Safe, DoozezUser, Invitation, ActionPayload, Participation, PaymentMethod, DoozezJob, DoozezTask, \
    Payment
from .fields import NullableJSONField


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoozezUser
        fields = ['id', 'email', 'first_name', 'last_name', 'groups']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['name']


class DoozezRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(allow_blank=True)
    last_name = serializers.CharField(allow_blank=True)

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', '')
        }


class SafeSerializer(serializers.ModelSerializer):
    payment_method_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Safe
        fields = ['id', 'status', 'name', 'monthly_payment', 'id', 'initiator', 'payment_method_id']


class InvitationReadSerializer(serializers.ModelSerializer):
    recipient = UserSerializer()
    sender = UserSerializer()
    safe = SafeSerializer()

    class Meta:
        model = Invitation
        fields = ['id', 'status', 'recipient', 'sender', 'safe']


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


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['id', 'is_default', 'name']


class PaymentMethodReadSerializer(serializers.ModelSerializer):
    redirect_url = serializers.CharField(source='gcflow.flow_redirect_url')

    class Meta:
        model = PaymentMethod
        fields = ['id', 'is_default', 'redirect_url', 'status', 'name']


class ParticipationListSerializer(serializers.ModelSerializer):
    user_role = serializers.CharField(source='get_user_role_display')
    status = serializers.CharField(source='get_status_display')
    user = UserSerializer()
    safe = SafeSerializer()

    class Meta:
        model = Participation
        fields = ['id', 'user_role', 'status', 'user', 'safe', 'win_sequence']


class ParticipationRetrieveSerializer(serializers.ModelSerializer):
    user_role = serializers.CharField(source='get_user_role_display')
    status = serializers.CharField(source='get_status_display')
    user = UserSerializer()
    safe = SafeSerializer()
    payment_method = PaymentMethodSerializer()

    class Meta:
        model = Participation
        fields = ['id', 'user_role', 'status', 'user', 'safe', 'payment_method', 'win_sequence']


class PaymentSerializer(serializers.ModelSerializer):
    participation = ParticipationRetrieveSerializer()

    class Meta:
        model = Payment
        fields = ['id', 'status', 'amount', 'charge_date', 'description', 'participation']


class TaskSerializer(serializers.ModelSerializer):
    task_type = serializers.CharField(source='get_task_type_display')

    class Meta:
        model = DoozezTask
        fields = ['id', 'created_on', 'status', 'task_type']


class JobSerializer(serializers.ModelSerializer):
    jobs_tasks = serializers.SerializerMethodField('get_tasks')

    class Meta:
        model = DoozezJob
        fields = ['id', 'created_on', 'status', 'jobs_tasks']

    def get_tasks(self, job):
        request = self.context.get('request')
        queried_status = request.query_params.get('status')
        task_queryset = DoozezTask.objects.filter(Q(job=job))
        if queried_status is not None:
            task_queryset = task_queryset.filter(Q(status=queried_status))
        serializer = TaskSerializer(instance=task_queryset, many=True, context=self.context)

        return serializer.data
