import json
import sys

from django.contrib.auth import get_user_model
from django.db import transaction
from djmoney.money import Money

from .client_interfaces import PaymentGatewayClient
from .models import Invitation, Safe, InvitationStatus, Participation, PaymentMethod, PaymentMethodStatus, \
    ParticipantRole, GCFlow, Mandate, DoozezTask, DoozezTaskStatus, ParticipationStatus, SafeStatus, PaymentStatus, \
    Payment, DoozezTaskType, DoozezJob, DoozezJobType, DoozezJobStatus
from .decorators import run

from django.core.exceptions import ValidationError
from django.db.models import Q

from .utils import exception_as_dict


class UserService(object):
    def __init__(self):
        self.User = get_user_model()

    def getSystemUser(self):
        return self.User.objects.filter(is_system=True).first()


class InvitationService(object):
    def __init__(self):
        pass

    def createInvitation(self, current_user, recipient, safe):
        if recipient.email == current_user.email:
            # sender can't be recipient
            raise ValidationError("recipient and sender can't be the same user")
        existing = Invitation.objects.filter(Q(recipient=recipient) &
                                             Q(safe=safe) &
                                             ~Q(status=InvitationStatus.Declined)).all()
        if len(existing) > 0:
            # duplicate invitations not allowed
            raise ValidationError("an existing invitation is found for user {} for safe {}", recipient, safe.pk)
        invitation = Invitation(sender=current_user, recipient=recipient, safe=safe)
        invitation.save()
        return invitation

    def acceptInvitation(self, invitation, payment_method_id, current_user):
        if invitation.status != InvitationStatus.Pending and invitation.status != InvitationStatus.Accepted:
            raise ValidationError("only pending or accepted invitations can be accepted")
        if invitation.recipient != current_user:
            raise ValidationError("only recipient can accept invite")
        participation_service = ParticipationService()
        payment_method_service = PaymentMethodService()
        payment_method = payment_method_service.getPaymentMethodsWithQ(
            Q(user=invitation.recipient) & Q(pk=payment_method_id)).first()
        if payment_method is None:
            raise ValidationError("no payment method found for user")
        participation_service.createParticipation(invitation.recipient, invitation, invitation.safe,
                                                  payment_method, ParticipantRole.Participant)
        invitation.accept()
        invitation.save()
        return invitation

    def declineInvitation(self, invitation, current_user):
        if invitation.recipient != current_user:
            raise ValidationError("only recipient can decline invite")
        if invitation.status != InvitationStatus.Pending and invitation.status != InvitationStatus.Declined:
            raise ValidationError("only pending or declined invitations can be declined")
        invitation.decline()
        invitation.save()
        return invitation

    def removeInvitation(self, invitation, current_user):
        if current_user.id != invitation.sender.id:
            raise ValidationError("only sender can remove invitation")
        if invitation.status != InvitationStatus.Pending:
            raise ValidationError(
                "only pending invitations can be removed by sender. current status is {}".format(invitation.status))
        invitation.removePendingInvitation()
        invitation.save()
        return invitation

    def getPendingInvitationsForSafe(self, safe):
        return Invitation.objects.filter(Q(status=InvitationStatus.Pending) & Q(safe=safe)).all()


class MandateService(object):
    def __init__(self):
        pass

    def createMandate(self, status, scheme, mandate_external_id):
        return Mandate.objects.create(status=status, scheme=scheme, mandate_external_id=mandate_external_id)

    def submitMandate(self, pk):
        mandate = Mandate.objects.get(pk=pk)
        if mandate is None:
            raise ValidationError("failed to find Mandate for pk {}".format(pk))
        mandate.submit()
        return mandate


class PaymentMethodService(object):
    mandate_service = MandateService()

    def __init__(self, access_token=None, environment=None):
        if access_token is None or environment is None:
            self.payment_gate_way_client = None
        else:
            self.payment_gate_way_client = PaymentGatewayClient(access_token, environment)

    def getPaymentMethodsWithQ(self, query):
        return PaymentMethod.objects.filter(query)

    def getAllPaymentMethodsForUser(self, user):
        return self.getPaymentMethodsWithQ(Q(user=user)).all()

    def getDefaultPaymentMethodForUser(self, user):
        return self.getPaymentMethodsWithQ(Q(user=user) & Q(is_default=True)).first()

    def createPaymentMethod(self, user, is_default, name, pgw_description, pgw_session_token, pgw_success_redirect_url):
        if self.payment_gate_way_client is None:
            raise AttributeError("payment gateway client is not initialized")
        redirect_flow = self.payment_gate_way_client.create_approval_flow(pgw_description, pgw_session_token,
                                                                          pgw_success_redirect_url, user)
        payment_method = PaymentMethod.objects.create(user=user, is_default=is_default, name=name)
        GCFlow.objects.create(flow_id=redirect_flow.redirect_id,
                              flow_redirect_url=redirect_flow.redirect_url,
                              session_token=pgw_session_token,
                              payment_method=payment_method)
        return payment_method

    def createPaymentMethodForUser(self, user, is_default, name, pgw_description, pgw_session_token,
                                   pgw_success_redirect_url):
        all = self.getAllPaymentMethodsForUser(user)
        if len(all) == 0:
            # first payment method is always default
            return self.createPaymentMethod(user=user, is_default=True, name=name,
                                            pgw_description=pgw_description,
                                            pgw_session_token=pgw_session_token,
                                            pgw_success_redirect_url=pgw_success_redirect_url)
        else:
            temp_is_default = is_default
            default = all.filter(is_default=True).first()
            if default is None:
                temp_is_default = True
            else:
                default.is_default = False
                default.save()
            return self.createPaymentMethod(user=user, is_default=temp_is_default, name=name,
                                            pgw_description=pgw_description,
                                            pgw_session_token=pgw_session_token,
                                            pgw_success_redirect_url=pgw_success_redirect_url)

    def approveWithExternalSuccessWithFlowId(self, flow_id):
        gcflow = GCFlow.objects.get(flow_id=flow_id)
        if gcflow is None:
            raise ValidationError("no flow object found")
        payment_method = gcflow.payment_method
        payment_method.approveWithExternalSuccess()
        confirmation_flow = self.payment_gate_way_client.complete_approval_flow(flow_id, gcflow.session_token)
        gcmandate = self.payment_gate_way_client.get_mandate(confirmation_flow.mandate_id)
        mandate = self.mandate_service.createMandate(status=gcmandate.status, scheme=gcmandate.scheme,
                                                     mandate_external_id=gcmandate.id)
        payment_method.mandate = mandate
        payment_method.save()
        return payment_method

    def failWithExternalFailed(self, pk):
        payment_method = self.getPaymentMethodsWithQ(Q(pk=pk)).first()
        payment_method.failApproveWithExternalFailed()
        return payment_method


class ParticipationService(object):
    user_service = UserService()
    payment_method_service = PaymentMethodService()

    def __init__(self):
        pass

    def getParticipationWithId(self, participation_id):
        return Participation.objects.get(pk=participation_id)

    def getParticipationWithQ(self, query):
        return Participation.objects.filter(query)

    def getParticipationForSafe(self, safe_id):
        return self.getParticipationWithQ(Q(safe__id=safe_id)).all()

    def createParticipation(self, user, invitation, safe, payment_method, role):
        participation = Participation(user=user, invitation=invitation, safe=safe,
                                      payment_method=payment_method, user_role=role)
        participation.save()
        return participation

    def createParticipationForSystemUser(self, safe):
        system_user = self.user_service.getSystemUser()
        if system_user is None:
            raise ValidationError("no system user found")
        # TODO: current payment_method is added as migration with no GCMandate. We need a proper setup
        #  process to create a new Mandate (if doesn't exist) and link it to default payment_method of
        #  system user.
        default_payment_method = self.payment_method_service.getDefaultPaymentMethodForUser(system_user)
        if default_payment_method is None:
            raise ValidationError("no payment method found for system user")
        return Participation.objects.create(user=system_user,
                                            safe=safe,
                                            user_role=ParticipantRole.System,
                                            payment_method=default_payment_method)

    def leaveSafe(self, pk, user_id):
        participation = Participation.objects.get(pk=pk)
        if user_id != participation.user.pk:
            raise ValidationError("user_id {} does not match participation user id {}. only participant can leave a "
                                  "participation".format(user_id, participation.user.pk))
        if participation is None:
            raise ValidationError("no participation found for pk {}".format(pk))
        if participation.status != ParticipationStatus.Active:
            raise ValidationError("participation for pk {} is not Active".format(pk))
        if participation.safe.status != SafeStatus.PendingParticipants:
            raise ValidationError(
                "participation can not be cancelled for an active safe. current safe status is {}".format(
                    participation.safe.status))
        participation.leaveActiveParticipation()
        participation.save()
        return participation


class PaymentService(object):
    participation_service = ParticipationService()

    def __init__(self, access_token=None, environment=None):
        if access_token is None or environment is None:
            self.payment_gate_way_client = None
        else:
            self.payment_gate_way_client = PaymentGatewayClient(access_token, environment)

    def createPayment(self, participation_id, amount, currency, description):
        participation = self.participation_service.getParticipationWithId(participation_id)
        if participation is None:
            raise ValidationError("participation not found for {}".format(str(participation_id)))
        external_payment = self.payment_gate_way_client.create_payment(
            participation.payment_method.mandate.mandate_external_id,
            amount,
            currency)
        payment = Payment.objects.create(participation=participation,
                                         amount=Money(amount, currency),
                                         description=description,
                                         external_id=external_payment.id)
        return payment


class TaskService(object):

    def __init__(self):
        pass

    def createTaskForJob(self, task_type, parameters, sequence, job):
        return DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=task_type,
                                         parameters=parameters, job=job, sequence=sequence)

    def getTasksWithConcurrencyWithQ(self, query):
        return DoozezTask.objects.select_for_update().filter(query)

    def getOrderedPendingTasksForJob(self, job_id):
        return self.getTasksWithConcurrencyWithQ(Q(status=DoozezTaskStatus.Pending) & Q(job=job_id)).order_by(
            'sequence', '-created_on')

    def getNextRunableTask(self, job_id):
        return self.getOrderedPendingTasksForJob(job_id).first()

    def runNextRunnableTask(self, job_id):
        task = None
        with transaction.atomic():
            task = self.getNextRunableTask(job_id)
            if task is None:
                return
            task.startRunning()
            task.save()
        try:
            result = run(task.task_type, **json.loads(task.parameters))
            task.finishSuccessfully()
            task.save()
            return result
        except Exception as ex:
            err = sys.exc_info()
            task.exceptions = json.dumps(exception_as_dict(ex, err))
            task.finishWithFailure()
            task.save()
            raise ex


class JobService(object):

    def __init__(self):
        pass

    def createJob(self, job_type, user):
        return DoozezJob.objects.create(job_type=job_type, user=user)

    def getJobsWithConcurrencyWithQ(self, query):
        return DoozezJob.objects.select_for_update().filter(query)

    def getOrderedPendingJobs(self):
        return self.getJobsWithConcurrencyWithQ(Q(status=DoozezJobStatus.Created)
                                                or Q(status=DoozezJobStatus.Running)).order_by('-created_on')

    def getNextRunableTask(self):
        return self.getOrderedPendingJobs().first()

    def runNextRunnableJob(self):
        job = None
        with transaction.atomic():
            job = self.getNextRunableTask()
            if job is None:
                return
            job.startRunning()
            job.save()
        return job

    def finishJobSuccefully(self, job_id):
        with transaction.atomic():
            job = self.getJobsWithConcurrencyWithQ(Q(pk=job_id)).first()
            job.finishSuccessfully()
            job.save()

    def finishJobWithFailure(self, job_id):
        with transaction.atomic():
            job = self.getJobsWithConcurrencyWithQ(Q(pk=job_id)).first()
            job.finishWithFailure()
            job.save()


class JobExecutor(object):
    task_service = TaskService()
    job_service = JobService()

    def __init__(self):
        pass

    def executeNextRunnableJob(self):
        job = self.job_service.runNextRunnableJob()
        if job is None:
            return
        try:
            task = self.task_service.getNextRunableTask(job.pk)
            if task is None:
                self.job_service.finishJobSuccefully(job.pk)
                return
            self.task_service.runNextRunnableTask(job.pk)
        except:
            self.job_service.finishJobWithFailure(job.pk)
        return


class TaskPlanner(object):
    task_service = TaskService()
    job_service = JobService()

    def __init__(self):
        pass

    def createTasksForStartSafe(self, safe, job, currency='GBP'):
        participations = safe.participations_safe.all()
        tasks = []
        task_count = 0
        for i in range(len(participations)):
            participation = participations[i]
            parameters = '{{"participation_id":"{}", "amount":"{}", "currency":"{}"}}'. \
                format(participation.pk, safe.monthly_payment, currency)
            tasks.append(self.task_service.createTaskForJob(
                DoozezTaskType.CreatePayment,
                parameters,
                i,
                job))
            task_count = i
        task_count += 1
        tasks.append(self.task_service.createTaskForJob(
            DoozezTaskType.Draw,
            '{{"safe_id":{}}}'.format(str(safe.pk)),
            task_count,
            job))
        return tasks

    def createJobForStartSafe(self, safe, current_user):
        job = self.job_service.createJob(DoozezJobType.StartSafe, current_user)
        self.createTasksForStartSafe(safe, job)
        return job


class SafeService(object):
    participation_service = ParticipationService()
    payment_method_service = PaymentMethodService()
    invitation_service = InvitationService()
    task_planner = TaskPlanner()

    def __init__(self):
        pass

    def getSafeWithId(self, safe_id):
        return Safe.objects.get(pk=safe_id)

    def createSafe(self, current_user, name, monthly_payment, payment_method_id):
        payment_method = self.payment_method_service.getAllPaymentMethodsForUser(current_user) \
            .filter(pk=payment_method_id).first()
        if payment_method is None:
            raise ValidationError("no payment method found for user")
        safe = Safe(name=name, monthly_payment=monthly_payment, total_participants=1,
                    initiator=current_user)
        safe.save()
        self.participation_service.createParticipationForSystemUser(safe)
        self.participation_service.createParticipation(user=current_user, safe=safe,
                                                       payment_method=payment_method,
                                                       role=ParticipantRole.Initiator,
                                                       invitation=None)
        return safe

    def validateSafeForStart(self, current_user, safe, force):
        if safe.initiator != current_user:
            return ValidationError("safe {} can only be started by its initiator".format(safe.pk))
        pending_invitations = self.invitation_service.getPendingInvitationsForSafe(safe)
        if len(pending_invitations) > 0:
            if not force:
                return ValidationError("safe {} has pending invitations".format(safe.pk))
        return None

    def removePendingInvitations(self, current_user, safe):
        pending_invitations = self.invitation_service.getPendingInvitationsForSafe(safe)
        with transaction.atomic():
            removed_invitations = [self.invitation_service.removeInvitation(inv, current_user)
                                   for inv in pending_invitations]
            for inv in removed_invitations:
                if not (inv.status == InvitationStatus.RemovedBySender):
                    raise ValidationError(
                        "safe {} to be in RemovedBySender status but it is {}".format(safe.pk, inv.status))

    def startSafe(self, current_user, safe, force):
        validation_error = self.validateSafeForStart(current_user, safe, force)
        if validation_error is not None:
            raise validation_error
        if force:
            self.removePendingInvitations(current_user, safe)
        job = self.task_planner.createJobForStartSafe(safe, current_user)
        safe.status = SafeStatus.Starting
        safe.job = job
        safe.save()
        return safe
