from django.contrib.auth.models import AbstractUser
from djmoney.models.fields import MoneyField
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
    REMOVE = 'REMOVE', _('Remove')
    LEAVE = 'LEAVE', _('Leave')
    START = 'START', _('Start')


class ActionPayload(models.Model):
    class Meta:
        managed = False
    action = models.CharField(max_length=60, choices=Action.choices)
    json_data = JSONField(null=True)


class DoozezUser(AbstractUser):
    username = None
    email = models.EmailField(_('email address'), unique=True)
    is_system = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = DoozezUserManager()

    def __str__(self):
        return self.email


class Profile(TimeStampedModel):
    user = models.OneToOneField(DoozezUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=200, null=True)
    profile_pic = models.ImageField(null=True, blank=True)


class DoozezExecutableStatus(models.TextChoices):
    Created = 'CRT', _('Created')
    Running = 'RNG', _('Running')
    Successful = 'SUC', _('Success')
    Failed = 'FLD', _('Failed')


class DoozezExecutable(TimeStampedModel):
    status = FSMField(
        choices=DoozezExecutableStatus.choices,
        default=DoozezExecutableStatus.Created,
        protected=True,
    )

    @transition(field=status, source=[DoozezExecutableStatus.Created],
                target=DoozezExecutableStatus.Running)
    def startRunning(self):
        pass

    @transition(field=status, source=[DoozezExecutableStatus.Running],
                target=DoozezExecutableStatus.Successful)
    def finishSuccessfully(self):
        pass

    @transition(field=status, source=[DoozezExecutableStatus.Running],
                target=DoozezExecutableStatus.Failed)
    def finishWithFailure(self):
        pass

    class Meta:
        abstract = True


class DoozezJobStatus(models.TextChoices):
    Created = 'CRT', _('Created')
    Running = 'RNG', _('Running')
    Successful = 'SUC', _('Success')
    Failed = 'FLD', _('Failed')


class DoozezJobType(models.TextChoices):
    StartSafe = 'SSF', _('StartSafe')


class DoozezJob(DoozezExecutable):
    job_type = models.CharField(
        max_length=3,
        choices=DoozezJobType.choices
    )
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')


class DoozezTaskStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Running = 'RUN', _('Running')
    Successful = 'SUC', _('Success')
    Failed = 'FLD', _('Failed')


class DoozezTaskType(models.TextChoices):
    Draw = 'DRW', _('Draw')
    CreatePayment = 'CTP', _('CreatePayment')
    CreateInstallments = 'CRI', _('CreateInstallments')
    CompleteSafeStart = 'CSS', _('CompleteSafeStart')


class DoozezTask(TimeStampedModel):
    status = FSMField(
        choices=DoozezTaskStatus.choices,
        default=DoozezTaskStatus.Pending,
        protected=True,
    )
    task_type = models.CharField(
        max_length=3,
        choices=DoozezTaskType.choices
    )
    parameters = JSONField(null=True)
    exceptions = JSONField(null=True)
    job = models.ForeignKey(DoozezJob, on_delete=models.CASCADE, related_name='jobs_tasks', null=True)
    sequence = models.PositiveIntegerField(default=0)

    @transition(field=status, source=[DoozezTaskStatus.Pending],
                target=DoozezTaskStatus.Running)
    def startRunning(self):
        pass

    @transition(field=status, source=[DoozezTaskStatus.Running],
                target=DoozezTaskStatus.Successful)
    def finishSuccessfully(self):
        pass

    @transition(field=status, source=[DoozezTaskStatus.Running],
                target=DoozezTaskStatus.Failed)
    def finishWithFailure(self):
        pass

    def __str__(self):
        return '%d, %s: status: %s, exceptions: %s' % (self.id, self.get_task_type_display(), self.get_status_display(), self.exceptions)


class GCEvent(models.Model):
    event_id = models.TextField()
    resource_type = models.TextField()
    action = models.TextField()
    link_id = models.TextField(null=True)
    cause = models.TextField(null=True)
    description = models.TextField(null=True)
    gc_created_at = models.TextField(null=True)


class Event(DoozezExecutable):
    gc_event = models.ForeignKey(GCEvent, on_delete=models.CASCADE, related_name='%(class)s_user', null=True)


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
    ExternallyCreated = 'EXC', _('ExternallyCreated')
    ExternallySubmitted = 'EXS', _('ExternallySubmitted')
    ExternallyActivated = 'EXA', _('ExternallyActivated')


class PaymentMethod(models.Model):
    status = FSMField(
        choices=PaymentMethodStatus.choices,
        default=PaymentMethodStatus.PendingExternalApproval,
        protected=True,
    )
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')
    is_default = models.BooleanField(default=False)
    mandate = models.ForeignKey(Mandate, on_delete=models.DO_NOTHING, null=True)
    name = models.CharField(max_length=500, null=True, blank=True)

    @transition(field=status, source=[PaymentMethodStatus.PendingExternalApproval],
                target=PaymentMethodStatus.ExternalApprovalSuccessful)
    def approveWithExternalSuccess(self):
        pass

    @transition(field=status, source=[PaymentMethodStatus.PendingExternalApproval],
                target=PaymentMethodStatus.ExternalApprovalFailed)
    def failApproveWithExternalFailed(self):
        pass

    @transition(field=status, source=[PaymentMethodStatus.ExternalApprovalSuccessful],
                target=PaymentMethodStatus.ExternallyCreated)
    def createdExternally(self):
        pass

    @transition(field=status, source=[PaymentMethodStatus.ExternallyCreated],
                target=PaymentMethodStatus.ExternallySubmitted)
    def submittedExternally(self):
        pass

    @transition(field=status, source=[PaymentMethodStatus.ExternallySubmitted],
                target=PaymentMethodStatus.ExternallyActivated)
    def activatedExternally(self):
        pass

    def is_active(self):
        return self.status == PaymentMethodStatus.ExternallyActivated


class SafeStatus(models.TextChoices):
    PendingParticipants = 'PPT', _('PendingParticipants')
    Starting = 'STG', _('Starting')
    Started = 'STD', _('Started')
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
    job = models.ForeignKey(DoozezJob, on_delete=models.DO_NOTHING, null=True, blank=True)

    def __str__(self):
        return self.name


class InvitationStatus(models.TextChoices):
    Pending = 'PND', _('Pending')
    Accepted = 'ACC', _('Accepted')
    Declined = 'DEC', _('Declined')
    RemovedBySender = 'RBS', _('RemovedBySender')


class Invitation(models.Model):
    status = FSMField(
        choices=InvitationStatus.choices,
        default=InvitationStatus.Pending,
        protected=True,
    )
    sender = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='sender')
    recipient = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='recipient')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE, related_name='invitations_safe')

    @transition(field=status, source=[InvitationStatus.Pending],
                target=InvitationStatus.Accepted)
    def accept(self):
        pass

    @transition(field=status, source=[InvitationStatus.Pending],
                target=InvitationStatus.Declined)
    def decline(self):
        pass

    @transition(field=status, source=[InvitationStatus.Pending],
                target=InvitationStatus.RemovedBySender)
    def removePendingInvitation(self):
        pass


class ParticipantRole(models.TextChoices):
    Initiator = 'INT', _('Initiator')
    Participant = 'PCT', _('Participant')
    System = 'SYS', _('System')


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
    status = FSMField(
        choices=ParticipationStatus.choices,
        default=ParticipationStatus.Active,
        protected=True,
    )
    invitation = models.ForeignKey(Invitation, on_delete=models.CASCADE, related_name='invitation', null=True)
    user = models.ForeignKey(DoozezUser, on_delete=models.CASCADE, related_name='%(class)s_user')
    safe = models.ForeignKey(Safe, on_delete=models.CASCADE, related_name='participations_safe')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name='payment_method')
    win_sequence = models.PositiveIntegerField(null=True)

    @transition(field=status, source=[ParticipationStatus.Active],
                target=ParticipationStatus.Left)
    def leaveActiveParticipation(self):
        pass


class PaymentStatus(models.TextChoices):
    PendingSubmission = 'pending_submission', _('PendingSubmission')
    Submitted = 'submitted', _('Submitted')
    Confirmed = 'confirmed', _('Confirmed')
    Failed = 'failed', _('Failed')
    Cancelled = 'cancelled', _('Cancelled')
    CustomerApprovalDenied = 'customer_approval_denied', _('CustomerApprovalDenied')
    ChargedBack = 'charged_back', _('ChargedBack')


class Payment(TimeStampedModel):
    status = FSMField(
        choices=PaymentStatus.choices,
        default=PaymentStatus.PendingSubmission,
        protected=True,
    )
    participation = models.ForeignKey(
        Participation,
        on_delete=models.CASCADE,
        related_name='payments_participation',
        null=True)
    amount = MoneyField(
        decimal_places=2,
        default=0,
        default_currency='GBP',
        max_digits=11,
    )
    charge_date = models.DateTimeField(null=True, blank=True)
    description = models.TextField()
    external_id = models.TextField(null=True, blank=True)

    @transition(field=status, source=[PaymentStatus.Submitted, PaymentStatus.PendingSubmission],
                target=PaymentStatus.Confirmed)
    def paymentConfirmed(self):
        pass


class GCFlow(models.Model):
    flow_id = models.TextField()
    flow_redirect_url = models.TextField(null=True)
    session_token = models.TextField()
    payment_method = models.OneToOneField(PaymentMethod, on_delete=models.CASCADE)

