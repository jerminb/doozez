from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from django_fsm import FSMField, transition

from .managers import DoozezUserManager


class TimeStampedModel(models.Model):
    created_on = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


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


class MandateStatus(models.TextChoices):
    PendingCustomerApproval = 'pending_customer_approval', _('pending_customer_approval')
    PendingSubmission = 'pending_submission', _('pending_submission')
    Submitted = 'submitted', _('submitted')
    Active = 'active', _('active')
    Failed = 'failed', _('failed')
    Cancelled = 'cancelled', _('cancelled')
    Expired = 'expired', _('expired')
    Consumed = 'consumed', _('consumed')


class Mandate(models.Model):
    status = FSMField(
        choices=MandateStatus.choices,
        default=MandateStatus.PendingSubmission,
        protected=True,
    )
    scheme = models.TextField()
    mandate_external_id = models.TextField()

    @transition(field=status, source=[MandateStatus.Submitted],
                target=MandateStatus.Active)
    def activate(self):
        # signal PaymentMethod
        pass

    @transition(field=status, source=[MandateStatus.PendingSubmission],
                target=MandateStatus.Submitted)
    def submit(self):
        # signal PaymentMethod
        pass


class PaymentMethodStatus(models.TextChoices):
    PendingExternalApproval = 'PEA', _('PendingExternalApproval')
    ExternalApprovalSuccessful = 'EAS', _('ExternalApprovalSuccessful')
    ExternalApprovalFailed = 'EAF', _('ExternalApprovalFailed')


class PaymentMethod(models.Model):
    status = FSMField(
        choices=PaymentMethodStatus.choices,
        default=PaymentMethodStatus.PendingExternalApproval,
        protected=True,
    )
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')
    is_default = models.BooleanField(default=False)
    mandate = models.ForeignKey(Mandate, on_delete=models.DO_NOTHING, null=True)

    @transition(field=status, source=[PaymentMethodStatus.PendingExternalApproval],
                target=PaymentMethodStatus.ExternalApprovalSuccessful)
    def approveWithExternalSuccess(self):
        pass

    @transition(field=status, source=[PaymentMethodStatus.PendingExternalApproval],
                target=PaymentMethodStatus.ExternalApprovalFailed)
    def failApproveWithExternalFailed(self):
        pass


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
    flow_redirect_url = models.TextField(null=True)
    session_token = models.TextField()
    payment_method = models.OneToOneField(PaymentMethod, on_delete=models.CASCADE)


class DoozezTaskStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Running = 'ACT', _('Running')
    Successful = 'SUC', _('Success')
    Failed = 'FLD', _('Failed')


class DoozezTaskType(models.TextChoices):
    Draw = 'DRW', _('Draw')
    WithdrawFirstPayment = 'WFP', _('WithdrawFirstPayment')
    CreateInstallments = 'CRI', _('CreateInstallments')
    CompleteSafeStart = 'CSS', _('CompleteSafeStart')


class DoozezTask(TimeStampedModel):
    status = models.CharField(
        max_length=3,
        choices=DoozezTaskStatus.choices,
        default=DoozezTaskStatus.Pending,
    )
    task_type = models.CharField(
        max_length=3,
        choices=DoozezTaskType.choices
    )
    parameters = JSONField(null=True)

