import json
import os
import uuid

from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.db.models import Q
from rest_framework import viewsets
from rest_framework import permissions, status
from rest_framework.decorators import action, permission_classes
from django.core.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from .permissions import IsOwner
from .serializers import UserSerializer, GroupSerializer, SafeSerializer, InvitationReadSerializer, \
    InvitationUpsertSerializer, ActionPayloadSerializer, ParticipationListSerializer, \
    ParticipationRetrieveSerializer, PaymentMethodSerializer, PaymentMethodReadSerializer, JobSerializer
from .models import Safe, DoozezUser, Invitation, Action, Participation, PaymentMethod, DoozezJob, InvitationStatus
from .services import InvitationService, SafeService, PaymentMethodService, ParticipationService


class ConfirmatioView(TemplateView):
    template_name = "confirmation.html"

    def get(self, request, *args, **kwargs):
        service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], os.environ['GC_ENVIRONMET'])
        flow_id = request.GET.get('redirect_flow_id')
        if flow_id is None:
            return HttpResponse('Error no redirect flow id found!')
        else:
            service.approveWithExternalSuccessWithFlowId(flow_id)
        return super().get(request, *args, **kwargs)


class OwnerViewSet(viewsets.ModelViewSet):
    def get_owner_filter(self):
        pass

    def get_queryset(self):
        query_set = self.queryset
        owner_filter = self.get_owner_filter()
        if owner_filter is not None:
            return query_set.filter(owner_filter)
        else:
            return query_set


class ReadOnlyOwnerViewSet(viewsets.ReadOnlyModelViewSet):
    def get_owner_filter(self):
        pass

    def get_queryset(self):
        query_set = self.queryset
        owner_filter = self.get_owner_filter()
        if owner_filter is not None:
            return query_set.filter(owner_filter)
        else:
            return query_set


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = DoozezUser.objects.all().order_by('-date_joined')
        email = self.request.query_params.get('email')
        if email is not None:
            queryset = queryset.filter(email__istartswith=email)
        return queryset


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]


class SafeViewSet(OwnerViewSet):
    """
    API endpoint that allows safes to be viewed or edited.
    """

    def get_owner_filter(self):
        user = self.request.user
        return Q(participations_safe__user=user) | \
               (Q(invitations_safe__recipient=user) & ~Q(invitations_safe__status=InvitationStatus.Declined))

    def get_queryset(self):
        result = super().get_queryset().distinct()
        return result

    def create(self, request):
        """
        Create an safe with current user as initiator
        """
        user = self.request.user
        serializer = SafeSerializer(data=request.data)
        service = SafeService()
        if serializer.is_valid():
            safe = service.createSafe(user, serializer.validated_data['name'],
                                      serializer.validated_data['monthly_payment'],
                                      serializer.validated_data['payment_method_id'])
            return Response(data=SafeSerializer(safe, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_value_from_json(self, json_data, key):
        extra_data = json.loads(json_data)
        return extra_data.get(key, None)

    def start_safe(self, json_data):
        service = SafeService()
        safe = self.get_object()
        force = self.get_value_from_json(json_data, 'force')
        if force is None:
            force = True
        return service.startSafe(self.request.user, safe, force)

    def partial_update(self, request, *args, **kwargs):
        serializer = ActionPayloadSerializer(data=request.data)
        if serializer.is_valid():
            options = {
                Action.START: self.start_safe,
            }
            try:
                job = options[serializer.validated_data['action']](serializer.validated_data['json_data'])
                return Response(data=JobSerializer(job, context={'request': request}).data,
                                status=status.HTTP_200_OK)
            except TypeError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    queryset = Safe.objects.all().order_by('id')
    serializer_class = SafeSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvitationViewSet(OwnerViewSet):
    """
    API endpoint that allows safes to be viewed or edited.
    """

    def get_owner_filter(self):
        user = self.request.user
        return Q(recipient=user) | Q(sender=user)

    def get_serializer_class(self):
        if self.request and (self.request.method == 'POST' or self.request.method == 'PUT'
                             or self.request.method == 'PATCH'):
            return InvitationUpsertSerializer
        else:
            return InvitationReadSerializer

    def get_queryset(self):
        """
        This view should return a list of all the invitations
        for the currently authenticated user.
        """
        safe = self.request.query_params.get('safe')
        result = super().get_queryset()
        if safe is not None:
            result = result.filter(safe__id=safe)
        return result

    def create(self, request):
        """
        Create an invitation with current user as Sender
        """
        user = self.request.user
        serializer = self.get_serializer_class()(data=request.data)
        if serializer.is_valid():
            invitation = self.invitation_service.createInvitation(user, serializer.validated_data['recipient'],
                                                                  serializer.validated_data['safe'])
            return Response(data=self.get_serializer_class()(invitation, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_payment_method_id_from_json(self, json_data):
        extra_data = json.loads(json_data)
        return extra_data.get("payment_method_id", None)

    def accept_invitation(self, json_data):
        invitation = self.get_object()
        payment_method_id = self.get_payment_method_id_from_json(json_data)
        if payment_method_id is None:
            raise ValueError("payment_method_id is null")
        return self.invitation_service.acceptInvitation(invitation, payment_method_id, self.request.user)

    def decline_invitation(self, json_data):
        invitation = self.get_object()
        return self.invitation_service.declineInvitation(invitation, self.request.user)

    def remove_invitation(self, json_data):
        invitation = self.get_object()
        return self.invitation_service.removeInvitation(invitation, self.request.user)

    def partial_update(self, request, *args, **kwargs):
        serializer = ActionPayloadSerializer(data=request.data)
        if serializer.is_valid():
            options = {Action.ACCEPT: self.accept_invitation,
                       Action.DECLINE: self.decline_invitation,
                       Action.REMOVE: self.remove_invitation,
                       }
            try:
                invitation = options[serializer.validated_data['action']](serializer.validated_data['json_data'])
                return Response(data=self.get_serializer_class()(invitation, context={'request': request}).data,
                                status=status.HTTP_200_OK)
            except TypeError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    permission_classes = [permissions.IsAuthenticated]
    invitation_service = InvitationService()
    queryset = Invitation.objects.all()


class ParticipationViewSet(viewsets.ModelViewSet):
    """
    ReadOnly ViewSet for Participation
    """

    def list(self, request):
        safe = self.request.query_params.get('safe')
        result = self.get_queryset()
        if safe is not None:
            result = result.filter(safe__id=safe)
        serializer = ParticipationListSerializer(result, many=True)
        return Response(serializer.data)

    def get_serializer_class(self):
        if self.action and (self.action == 'list'):
            return ParticipationListSerializer
        else:
            return ParticipationRetrieveSerializer

    def leave_participation(self, json_data):
        participation = self.get_object()
        return self.participation_service.leaveSafe(participation.pk, self.request.user.pk)

    def create(self, request):
        return Response("", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, pk=None):
        return Response("", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, pk=None):
        return Response("", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        serializer = ActionPayloadSerializer(data=request.data)
        if serializer.is_valid():
            options = {
                Action.LEAVE: self.leave_participation,
            }
            try:
                participation = options[serializer.validated_data['action']](serializer.validated_data['json_data'])
                return Response(data=self.get_serializer_class()(participation, context={'request': request}).data,
                                status=status.HTTP_200_OK)
            except TypeError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
            except ValidationError as exp:
                return Response(repr(exp), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    queryset = Participation.objects.all()
    serializer_class = ParticipationListSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    participation_service = ParticipationService()


class PaymentMethodViewSet(OwnerViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = PaymentMethod.objects.all()

    def get_owner_filter(self):
        user = self.request.user
        return Q(user=user)

    def get_serializer_class(self):
        if self.request and (self.request.method == 'POST' or self.request.method == 'PUT'
                             or self.request.method == 'PATCH'):
            return PaymentMethodSerializer
        else:
            return PaymentMethodReadSerializer

    def create(self, request):
        """
        Create a payment-method for current user
        """
        user = self.request.user
        serializer = self.get_serializer_class()(data=request.data)
        service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], os.environ['GC_ENVIRONMET'])
        if serializer.is_valid():
            payment_method = service.createPaymentMethodForUser(user,
                                                                serializer.validated_data['is_default'],
                                                                serializer.validated_data['name'],
                                                                "Doozez",
                                                                str(uuid.uuid4()),
                                                                "https://developer.gocardless.com/example-redirect-uri/")
            return Response(data=PaymentMethodReadSerializer(payment_method, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JobsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for Jobs
    """

    queryset = DoozezJob.objects.all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'], url_path='tasks/')
    def get_with_task_status(self, request, *args, **kwargs):
        job = self.get_object()
        serializer = self.get_serializer_class()(job, context={'request': request})
        return Response(serializer.data)


class TokensViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request, *args, **kwargs):
        return Response("", status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=True)
    def get_user_for_token(self, request, *args, **kwargs):
        return Response(data=UserSerializer(self.request.user, context={'request': request}).data,
                        status=status.HTTP_200_OK)
