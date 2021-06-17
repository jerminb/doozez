from django.shortcuts import render
from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions

from .serializers import UserSerializer, GroupSerializer, SafeSerializer, InvitationSerializer
from .models import Safe, DoozezUser, Invitation


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = DoozezUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


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
    queryset = Safe.objects.all().order_by('id')
    serializer_class = SafeSerializer
    permission_classes = [permissions.IsAuthenticated]


class InvitationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows safes to be viewed or edited.
    """
    queryset = Invitation.objects.all().order_by('id')
    serializer_class = InvitationSerializer
    permission_classes = [permissions.IsAuthenticated]
