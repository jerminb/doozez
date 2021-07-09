from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField

from .managers import DoozezUserManager


class Action(models.TextChoices):
    ACCEPT = 'ACCEPT', _('Accept')
    DECLINE = 'DECLINE', _('Decline')


class ActionPayload(models.Model):
    class Meta:
        managed = False
    action = models.CharField(max_length=60, choices=Action.choices)
    json_data = JSONField(null=True)


class DoozezUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = DoozezUserManager()

    def __str__(self):
        return self.email


class PaymentMethodStatus(models.TextChoices):
    PendingExternalApproval = 'PEA', _('PendingExternalApproval')
    ExternalApprovalSuccessful = 'EAS', _('ExternalApprovalSuccessful')
    ExternalApprovalFailed = 'EAF', _('ExternalApprovalFailed')


class PaymentMethod(models.Model):
    status = models.CharField(
        max_length=3,
        choices=PaymentMethodStatus.choices,
        default=PaymentMethodStatus.PendingExternalApproval,
    )
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')
    is_default = models.BooleanField(default=False)


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
        unique_together = (('recipient', 'safe'),)

    status = models.CharField(
        max_length=3,
        choices=InvitationStatus.choices,
        default=InvitationStatus.Pending,
    )
    sender = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='sender')
    recipient = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='recipient')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE)


class ParticipantRole(models.TextChoices):
    Initiator = 'INT', _('Initiator')
    Participant = 'PCT', _('Participant')


class ParticipationStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Active = 'ACT', _('Active')
    Complete = 'CPT', _('Complete')
    PendingPayment = 'PPT', _('PendingPayment')
    Left = 'LEF', _('Left')


class Participation(models.Model):
    user_role = status = models.CharField(
        max_length=3,
        choices=ParticipantRole.choices,
        default=ParticipantRole.Participant,
    )
    status = models.CharField(
        max_length=3,
        choices=ParticipationStatus.choices,
        default=ParticipationStatus.Pending,
    )
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE, related_name='invitation', null=True)
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE, related_name='safe')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='payment_method')
    win_sequence = models.PositiveIntegerField(null=True)


class GCFlow(models.Model):
    flow_id = models.TextField()
    session_token = models.TextField()
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.CASCADE, related_name='%(class)s_payment_method')
