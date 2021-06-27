from django.shortcuts import render
from django.contrib.auth.models import Group
from django.db.models import Q
from rest_framework import viewsets
from rest_framework import permissions, status
from rest_framework.response import Response

from .serializers import UserSerializer, GroupSerializer, SafeSerializer, InvitationReadSerializer, InvitationUpsertSerializer
from .models import Safe, DoozezUser, Invitation
from .services import InvitationService, SafeService


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
        Create an invitation with current user as Sender
        """
        user = self.request.user
        serializer = SafeSerializer(data=request.data)
        service = SafeService()
        if serializer.is_valid():
            safe = service.createSafe(user, serializer.validated_data['name'], serializer.validated_data['monthly_payment'])
            return Response(data=SafeSerializer(safe, context={'request': request}).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    queryset = Safe.objects.all().order_by('id')
    serializer_class = SafeSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvitationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows safes to be viewed or edited.
    """
    def get_serializer_class(self):
        if self.request and (self.request.method == 'POST' or self.request.method == 'PUT'):
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
        service = InvitationService()
        if serializer.is_valid():
            invitation = service.createInvitation(user, serializer.validated_data['recipient'], serializer.validated_data['safe'])
            return Response(data=self.get_serializer_class()(invitation, context={'request': request}).data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    permission_classes = [permissions.IsAuthenticated]
