from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from .models import Safe
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
