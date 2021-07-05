from .models import Invitation, Safe, InvitationStatus, Participation, PaymentMethod, ParticipantRole

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

    def acceptInvitation(self, invitation, payment_method_id):
        if invitation.status != InvitationStatus.Pending and invitation.status != InvitationStatus.Accepted:
            raise ValidationError("only pending or accepted invitations can be accepted")
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

    def createParticipation(self, user, invitation, safe, payment_method, role):
        participation = Participation(user=user, invitation=invitation, safe=safe,
                                      payment_method=payment_method, user_role=role)
        participation.save()
        return participation


class PaymentMethodService(object):
    def __init__(self):
        pass

    def getPaymentMethodsWithQ(self, query):
        return PaymentMethod.objects.filter(query)

    def getAllPaymentMethodsForUser(self, user):
        return self.getPaymentMethodsWithQ(Q(user=user)).all()

    def getDefaultPaymentMethodForUser(self, user):
        return self.getPaymentMethodsWithQ(Q(user=user) & Q(is_default=True)).first()

    def createPaymentMethodForUser(self, user, is_default):
        all = self.getAllPaymentMethodsForUser(user)
        if len(all) == 0:
            # first payment method is always default
            return PaymentMethod.objects.create(user=user, is_default=True)
        else:
            temp_is_default = is_default
            default = all.filter(is_default=True).first()
            if default is None:
                temp_is_default = True
            else:
                default.is_default = False
                default.save()
            return PaymentMethod.objects.create(user=user, is_default=temp_is_default)

class SafeService(object):
    participation_service = ParticipationService()
    payment_method_service = PaymentMethodService()

    def __init__(self):
        pass

    def createSafe(self, current_user, name, monthly_payment):
        payment_method = self.payment_method_service.getDefaultPaymentMethodForUser(current_user)
        if payment_method is None:
            raise ValidationError("no payment method found for user")
        safe = Safe(name=name, monthly_payment=monthly_payment, total_participants=1, initiator=current_user)
        safe.save()
        self.participation_service.createParticipation(user=current_user, safe=safe,
                                                       payment_method=payment_method,
                                                       role=ParticipantRole.Initiator,
                                                       invitation=None)
        return safe
