from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from .models import Safe, PaymentMethod, InvitationStatus
from .services import InvitationService


class ServiceTest(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_recipient_cant_be_sender(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        with self.assertRaises(ValidationError):
            service.createInvitation(alice, alice, safe)

    def test_unique_recipient_per_safe(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        service.createInvitation(alice, bob, safe)
        with self.assertRaises(IntegrityError):
            service.createInvitation(alice, bob, safe)

    def test_accept_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        invitation = service.acceptInvitation(invitation)
        self.assertEqual(invitation.status, InvitationStatus.Accepted)

    def test_accept_invite_with_no_payment_method(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation)
