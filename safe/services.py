from .models import Invitation, Safe
from django.core.exceptions import ValidationError


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


class SafeService(object):
    def __init__(self):
        pass

    def createSafe(self, current_user, name, monthly_payment):
        safe = Safe(name=name, monthly_payment=monthly_payment, total_participants=1, initiator=current_user)
        safe.save()
        return safe
