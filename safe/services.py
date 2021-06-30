from .models import Invitation, Safe, InvitationStatus, Participation, PaymentMethod

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

    def acceptInvitation(self, invitation):
        if invitation.status != InvitationStatus.Pending and invitation.status != InvitationStatus.Accepted:
            raise ValidationError("only pending or accepted invitations can be accepted")
        participation_service = ParticipationService()
        payment_method_service = PaymentMethodService()
        payment_method = payment_method_service.getDefaultPaymentMethodForUser(invitation.recipient)
        if payment_method is None:
            raise ValidationError("no payment method found for user")
        participation_service.createParticipation(invitation.recipient, invitation, invitation.safe, payment_method)
        invitation.status = InvitationStatus.Accepted
        invitation.save()
        return invitation


class SafeService(object):
    def __init__(self):
        pass

    def createSafe(self, current_user, name, monthly_payment):
        safe = Safe(name=name, monthly_payment=monthly_payment, total_participants=1, initiator=current_user)
        safe.save()
        return safe


class ParticipationService(object):
    def __init__(self):
        pass

    def createParticipation(self, user, invitation, safe, payment_method):
        participation = Participation(user=user, invitation=invitation, safe=safe, payment_method=payment_method)
        participation.save()
        return participation


class PaymentMethodService(object):
    def __init__(self):
        pass

    def getDefaultPaymentMethodForUser(self, user):
        return PaymentMethod.objects.filter(Q(user=user) & Q(is_default=True)).first()
