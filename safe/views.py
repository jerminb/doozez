import json

from django.contrib.auth.models import Group
from django.db.models import Q
from rest_framework import viewsets
from rest_framework import permissions, status
from rest_framework.response import Response

from .serializers import UserSerializer, GroupSerializer, SafeSerializer, InvitationReadSerializer, \
    InvitationUpsertSerializer, ActionPayloadSerializer, ParticipationSerializer, PaymentMethodSerializer
from .models import Safe, DoozezUser, Invitation, Action, Participation, PaymentMethod
from .services import InvitationService, SafeService, PaymentMethodService


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


class SafeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows safes to be viewed or edited.
    """

    def create(self, request):
        """
        Create an safe with current user as initiator
        """
        user = self.request.user
        serializer = SafeSerializer(data=request.data)
        service = SafeService()
        if serializer.is_valid():
            safe = service.createSafe(user, serializer.validated_data['name'],
                                      serializer.validated_data['monthly_payment'])
            return Response(data=SafeSerializer(safe, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    queryset = Safe.objects.all().order_by('id')
    serializer_class = SafeSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvitationViewSet(viewsets.ModelViewSet):
    invitation_service = InvitationService()
    """
    API endpoint that allows safes to be viewed or edited.
    """

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
        user = self.request.user
        safe = self.request.query_params.get('safe')
        result = Invitation.objects.filter(Q(recipient=user) | Q(sender=user))
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
        return self.invitation_service.acceptInvitation(invitation, payment_method_id)

    def decline_invitation(self, json_data):
        invitation = self.get_object()
        return self.invitation_service.declineInvitation(invitation)

    def partial_update(self, request, *args, **kwargs):
        serializer = ActionPayloadSerializer(data=request.data)
        if serializer.is_valid():
            options = {Action.ACCEPT: self.accept_invitation,
                       Action.DECLINE: self.decline_invitation,
                       }
            invitation = options[serializer.validated_data['action']](serializer.validated_data['json_data'])
            return Response(data=self.get_serializer_class()(invitation, context={'request': request}).data,
                            status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    permission_classes = [permissions.IsAuthenticated]


class ParticipationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for Participation
    """
    queryset = Participation.objects.all()
    serializer_class = ParticipationSerializer
    permission_classes = [permissions.IsAuthenticated]


class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        This view should return a list of all the PaymentMethods
        for the currently authenticated user.
        """
        user = self.request.user
        result = PaymentMethod.objects.filter(Q(user=user))
        return result

    def create(self, request):
        """
        Create a payment-method for current user
        """
        user = self.request.user
        serializer = self.get_serializer_class()(data=request.data)
        service = PaymentMethodService()
        if serializer.is_valid():
            payment_method = service.createPaymentMethodForUser(user,
                                                serializer.validated_data['is_default'])
            return Response(data=self.get_serializer_class()(payment_method, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
