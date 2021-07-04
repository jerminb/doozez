from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from .models import Safe, PaymentMethod, InvitationStatus, Participation, ParticipantRole
from .services import InvitationService, SafeService, PaymentMethodService


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
        participation = Participation.objects.first()
        self.assertEqual(invitation.status, InvitationStatus.Accepted)
        self.assertEqual(participation.user.pk, 2)
        self.assertEqual(participation.user_role, ParticipantRole.Participant)

    def test_accept_invite_with_no_payment_method(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation)

    def test_participant_after_create_safe(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        PaymentMethod.objects.create(user=alice, is_default=True)
        service = SafeService()
        service.createSafe(alice, 'foosafe', 1)
        participation = Participation.objects.first()
        self.assertEqual(participation.user.pk, 1)
        self.assertEqual(participation.user_role, ParticipantRole.Initiator)

    def test_get_all_payments_for_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        PaymentMethod.objects.create(user=alice, is_default=True)
        PaymentMethod.objects.create(user=alice, is_default=False)
        payment_methods = PaymentMethodService().getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(len(payment_methods), 2)

    def test_create_payments_for_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        pm1 = PaymentMethodService().createPaymentMethodForUser(user=alice, is_default=False)
        self.assertEqual(pm1.is_default, True)
        pm2 = PaymentMethodService().createPaymentMethodForUser(user=alice, is_default=True)
        self.assertEqual(pm2.is_default, True)
        payment_methods = PaymentMethodService().getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(payment_methods[0].is_default, False)
