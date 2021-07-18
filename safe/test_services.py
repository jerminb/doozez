import os
from collections import namedtuple

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from unittest import mock
from .decorators import clear, doozez_task

from .models import Safe, PaymentMethod, InvitationStatus, Participation, ParticipantRole, PaymentMethodStatus, \
    MandateStatus, DoozezTask, DoozezTaskStatus, DoozezTaskType
from .services import InvitationService, SafeService, PaymentMethodService, TaskService


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
        payment_method = PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        invitation = service.acceptInvitation(invitation, payment_method.pk, bob)
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
            service.acceptInvitation(invitation, 1, bob)

    def test_accept_invite_others_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation, 1, alice)

    def test_participant_after_create_safe(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        service = SafeService()
        service.createSafe(alice, 'foosafe', 1, payment_method.pk)
        participation = Participation.objects.first()
        self.assertEqual(participation.user.pk, 1)
        self.assertEqual(participation.user_role, ParticipantRole.Initiator)

    def test_get_all_payments_for_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        PaymentMethod.objects.create(user=alice, is_default=True)
        PaymentMethod.objects.create(user=alice, is_default=False)
        payment_methods = PaymentMethodService("", "").getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(len(payment_methods), 2)

    @mock.patch('gocardless_pro.Client.redirect_flows')
    def test_create_payments_for_user(self, mock_gc):
        expected_dict = {
            "id": "foo",
            "redirect_url": "bar"
        }
        mock_gc.create.return_value = namedtuple("RedirectFlow", expected_dict.keys())(*expected_dict.values())
        payment_method_service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        pm1 = payment_method_service.createPaymentMethodForUser(user=alice, is_default=False,
                                                                pgw_description="desc", pgw_session_token="token",
                                                                pgw_success_redirect_url="url")
        self.assertEqual(pm1.is_default, True)
        self.assertEqual(pm1.gcflow.flow_id, 'foo')
        self.assertEqual(pm1.gcflow.flow_redirect_url, 'bar')
        pm2 = payment_method_service.createPaymentMethodForUser(user=alice, is_default=True,
                                                                pgw_description="desc", pgw_session_token="token",
                                                                pgw_success_redirect_url="url")
        self.assertEqual(pm2.is_default, True)
        self.assertEqual(pm1.gcflow.flow_id, 'foo')
        payment_methods = payment_method_service.getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(payment_methods[0].is_default, False)
        self.assertEqual(payment_methods[0].status, PaymentMethodStatus.PendingExternalApproval)

    @mock.patch('safe.client_interfaces.gocardless_pro.Client.mandates')
    @mock.patch('gocardless_pro.Client.redirect_flows')
    def test_approve_payment_method(self, mock_gc, mock_gc_services):
        expected_dict = {
            "id": "foo",
            "redirect_url": "bar"
        }
        mock_gc.create.return_value = namedtuple("RedirectFlow", expected_dict.keys())(*expected_dict.values())
        expected_link_dict = {
            "mandate": "foo_mandate",
            "customer": "foo_customer"
        }
        expected_link = namedtuple("ConfirmationLink", expected_link_dict.keys())(
            *expected_link_dict.values())
        expected_complete_dict = {
            "links": expected_link,
            "confirmation_urls": "bar"
        }
        mock_gc.complete.return_value = namedtuple("ConfirmationRedirectFlow", expected_complete_dict.keys())(
            *expected_complete_dict.values())
        expected_mandate_dict = {
            "id": "foo_mandate",
            "scheme": "bacs",
            "status": "pending_submission"
        }
        mock_gc_services.get.return_value = namedtuple("GCMandate", expected_mandate_dict.keys())(
            *expected_mandate_dict.values())
        payment_method_service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method_service.createPaymentMethodForUser(user=alice, is_default=False,
                                                          pgw_description="desc", pgw_session_token="token",
                                                          pgw_success_redirect_url="url")
        payment_method_service.approveWithExternalSuccessWithFlowId(flow_id="foo")
        payment_methods = payment_method_service.getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(payment_methods[0].status, PaymentMethodStatus.ExternalApprovalSuccessful)
        self.assertEqual(payment_methods[0].mandate.status, MandateStatus.PendingSubmission)

    def test_task_service_run(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(safe_id):
            return safe_id

        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,parameters='{"safe_id":1}')
        service = TaskService()
        result = service.runNextRunnableTask()
        self.assertEqual(result, 1)
