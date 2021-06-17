from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from .managers import DoozezUserManager


class DoozezUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = DoozezUserManager()

    def __str__(self):
        return self.email


class Safe(models.Model):
    name = models.CharField(max_length=60)
    id = models.AutoField(primary_key = True)

    def __str__(self):
        return self.name


class InvitationStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Accepted = 'ACC', _('Accepted')
    Declined = 'DEC', _('Declined')


class Invitation(models.Model):
    status = models.CharField(
        max_length=3,
        choices=InvitationStatus.choices,
        default=InvitationStatus.Pending,
    )
    sender = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='sender')
    recipient = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='recipient')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE)
