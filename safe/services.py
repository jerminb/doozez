import json

from django.db import transaction

from .client_interfaces import PaymentGatewayClient
from .models import Invitation, Safe, InvitationStatus, Participation, PaymentMethod, PaymentMethodStatus, \
    ParticipantRole, GCFlow, Mandate, DoozezTask, DoozezTaskStatus
from .decorators import run

from django.core.exceptions import ValidationError
from django.db.models import Q


class InvitationService(object):
    def __init__(self):
        pass

    def createInvitation(self, current_user, recipient, safe):
        if recipient.email == current_user.email:
            # sender can't be recipient
            raise ValidationError("recipient and sender can't be the same user")
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
        invitation.status = InvitationStatus.Accepted
        invitation.save()
        return invitation

    def declineInvitation(self, invitation):
        if invitation.status != InvitationStatus.Pending and invitation.status != InvitationStatus.Declined:
            raise ValidationError("only pending or declined invitations can be declined")
        invitation.status = InvitationStatus.Declined
        invitation.save()
        return invitation


class ParticipationService(object):
    def __init__(self):
        pass

    def getParticipationWithQ(self, query):
        return Participation.objects.filter(query)

    def getParticipationForSafe(self, safe_id):
        return self.getParticipationWithQ(Q(safe__id=safe_id)).all()

    def createParticipation(self, user, invitation, safe, payment_method, role):
        participation = Participation(user=user, invitation=invitation, safe=safe,
                                      payment_method=payment_method, user_role=role)
        participation.save()
        return participation


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

    def createPaymentMethod(self, user, is_default, pgw_description, pgw_session_token, pgw_success_redirect_url):
        if self.payment_gate_way_client is None:
            raise AttributeError("payment gateway client is not initialized")
        redirect_flow = self.payment_gate_way_client.create_approval_flow(pgw_description, pgw_session_token,
                                                                          pgw_success_redirect_url, user)
        payment_method = PaymentMethod.objects.create(user=user, is_default=is_default)
        GCFlow.objects.create(flow_id=redirect_flow.redirect_id,
                              flow_redirect_url=redirect_flow.redirect_url,
                              session_token=pgw_session_token,
                              payment_method=payment_method)
        return payment_method

    def createPaymentMethodForUser(self, user, is_default, pgw_description, pgw_session_token,
                                   pgw_success_redirect_url):
        all = self.getAllPaymentMethodsForUser(user)
        if len(all) == 0:
            # first payment method is always default
            return self.createPaymentMethod(user=user, is_default=True,
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
            return self.createPaymentMethod(user=user, is_default=temp_is_default,
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


class SafeService(object):
    participation_service = ParticipationService()
    payment_method_service = PaymentMethodService()

    def __init__(self):
        pass

    def createSafe(self, current_user, name, monthly_payment, payment_method_id):
        payment_method = self.payment_method_service.getAllPaymentMethodsForUser(current_user) \
            .filter(pk=payment_method_id).first()
        if payment_method is None:
            raise ValidationError("no payment method found for user")
        safe = Safe(name=name, monthly_payment=monthly_payment, total_participants=1,
                    initiator=current_user)
        safe.save()
        self.participation_service.createParticipation(user=current_user, safe=safe,
                                                       payment_method=payment_method,
                                                       role=ParticipantRole.Initiator,
                                                       invitation=None)
        return safe


class TaskService(object):

    def __init__(self):
        pass

    def getTasksWithConcurrencyWithQ(self, query):
        return DoozezTask.objects.select_for_update().filter(query)

    def getPendingTasksOrderedbyCreationDate(self):
        return self.getTasksWithConcurrencyWithQ(Q(status=DoozezTaskStatus.Pending)).order_by('-created_on')

    def getNextRunableTask(self):
        return self.getPendingTasksOrderedbyCreationDate().first()

    def runNextRunnableTask(self):
        task = None
        with transaction.atomic():
            task = self.getNextRunableTask()
            if task is None:
                return
            task.status = DoozezTaskStatus.Running
            task.save()
        return run(task.task_type, **json.loads(task.parameters))
