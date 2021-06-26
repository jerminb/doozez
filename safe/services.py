from .models import Invitation, InvitationStatus


class InvitationService(object):
    def __init__(self):
        pass

    def createInvitation(self, current_user, recipient, safe):
        invitation = Invitation(status=InvitationStatus.Pending, sender=current_user, recipient=recipient, safe=safe)
        invitation.save()
        return invitation