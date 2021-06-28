from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
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


class SafeStatus(models.TextChoices):
    PendingParticipants = 'PPT', _('PendingParticipants')
    PendingDraw = 'PDR', _('PendingDraw')
    PendingEntryPayment = 'PEP', _('PendingEntryPayment')
    Active = 'ACT', _('Active')
    Complete = 'CPT', _('Complete')


class Safe(models.Model):
    status = models.CharField(
        max_length=3,
        choices=SafeStatus.choices,
        default=SafeStatus.PendingParticipants,
    )
    name = models.CharField(max_length=60)
    monthly_payment = models.FloatField(validators=[MinValueValidator(0.0), ], default=0)
    total_participants = models.PositiveIntegerField(default=0)
    initiator = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='initiator', null=True)

    def __str__(self):
        return self.name


class InvitationStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Accepted = 'ACC', _('Accepted')
    Declined = 'DEC', _('Declined')


class Invitation(models.Model):
    class Meta:
        unique_together = (('sender', 'safe'),)

    status = models.CharField(
        max_length=3,
        choices=InvitationStatus.choices,
        default=InvitationStatus.Pending,
    )
    sender = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='sender')
    recipient = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='recipient')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE)
