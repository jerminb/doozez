import os
from collections import namedtuple
from unittest.mock import create_autospec

from django.db.models import Q
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest import mock

from djmoney.money import Money

from . import utils
from .decorators import clear, doozez_task

from .models import Safe, PaymentMethod, InvitationStatus, Participation, ParticipantRole, PaymentMethodStatus, \
    MandateStatus, DoozezTask, DoozezTaskStatus, DoozezTaskType, DoozezJob, DoozezJobType, SafeStatus, \
    ParticipationStatus, Mandate, PaymentStatus, Invitation, DoozezExecutableStatus, Event, Instalment, \
    InstalmentStatus, Payment, Product
from .notification import NotificationProvider
from .services import InvitationService, SafeService, PaymentMethodService, TaskService, UserService, \
    ParticipationService, PaymentService, TaskPlanner, JobService, JobExecutor, EventExecutor, EventService, \
    NotificationService, EventType, InstalmentService, PokeType


class ServiceTest(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_system_user(self):
        service = UserService()
        self.assertEqual(service.getSystemUser().email, 'system@doozez.internal')

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
        with self.assertRaises(ValidationError):
            service.createInvitation(alice, bob, safe)

    def test_unique_recipient_per_safe_with_declined_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        service.declineInvitation(invitation, bob)
        invitation = service.createInvitation(alice, bob, safe)
        self.assertEqual(invitation.status, InvitationStatus.Pending)

    def test_get_invite_for_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = InvitationService()
        service.createInvitation(alice, bob, safe)
        alice_invites = service.getPendingInvitationsForUser(alice)
        self.assertEqual(len(alice_invites), 0)
        bob_invites = service.getPendingInvitationsForUser(bob)
        self.assertEqual(len(bob_invites), 1)

    def test_accept_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        product = Product.objects.create(name="prodfoo", price=10)
        payment_method = PaymentMethod.objects.create(user=bob,
                                                      is_default=True,
                                                      status=PaymentMethodStatus.ExternallyActivated)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        invitation = service.acceptInvitation(invitation, payment_method.pk, product.pk, bob)
        participation = Participation.objects.first()
        self.assertEqual(invitation.status, InvitationStatus.Accepted)
        self.assertEqual(participation.user.pk, bob.pk)
        self.assertEqual(participation.user_role, ParticipantRole.Participant)
        self.assertEqual(participation.product.pk, product.pk)

    def test_accept_invite_with_notification(self):
        mock_service = create_autospec(NotificationService)
        mock_service.notify_invitation_created.return_value = None
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        payment_method = PaymentMethod.objects.create(user=bob,
                                                      is_default=True,
                                                      status=PaymentMethodStatus.ExternallyActivated)
        product = Product.objects.create(name="prodfoo", price=10)
        service = InvitationService(mock_service)
        invitation = service.createInvitation(alice, bob, safe)
        invitation = service.acceptInvitation(invitation, payment_method.pk, product.pk, bob)
        participation = Participation.objects.first()
        self.assertEqual(invitation.status, InvitationStatus.Accepted)
        self.assertEqual(participation.user.pk, bob.pk)
        self.assertEqual(participation.user_role, ParticipantRole.Participant)
        mock_service.notify_invitation_created.assert_called_once_with(bob, alice, safe)

    def test_accept_invite_with_no_payment_method(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        product = Product.objects.create(name="prodfoo", price=10)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation, 1, product.pk, bob)

    def test_accept_invite_without_active_payment_method(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=bob,
                                                      is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        product = Product.objects.create(name="prodfoo", price=10)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation, payment_method.pk, product.pk, bob)

    def test_accept_invite_others_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        payment_method = PaymentMethod.objects.create(user=bob, is_default=True)
        product = Product.objects.create(name="prodfoo", price=10)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.acceptInvitation(invitation, payment_method.pk, product.pk, alice)

    def test_remove_invite(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        invitation = service.removeInvitation(invitation, alice)
        self.assertEqual(invitation.status, InvitationStatus.RemovedBySender)

    def test_remove_invite_with_non_sender(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        with self.assertRaises(ValidationError):
            service.removeInvitation(invitation, bob)

    def test_create_participation_for_system_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        service = ParticipationService()
        participation = service.createParticipationForSystemUser(safe)
        self.assertEqual(participation.user.is_system, True)

    def test_participant_after_create_safe(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice,
                                                      is_default=True,
                                                      status=PaymentMethodStatus.ExternallyActivated)
        product = Product.objects.create(name="prodfoo", price=10)
        service = SafeService()
        participation_service = ParticipationService()
        safe = service.createSafe(alice, 'foosafe', 1, payment_method.pk, product.pk)
        participations = participation_service.getParticipationForSafe(safe_id=safe.pk)
        participation = participations.filter(user=alice).first()
        self.assertEqual(len(participations), 2)
        self.assertEqual(participation.user.pk, alice.pk)
        self.assertEqual(participation.user_role, ParticipantRole.Initiator)
        self.assertEqual(participation.product.pk, product.pk)
        participation = participations.filter(user__is_system=True).first()
        self.assertEqual(participation.user_role, ParticipantRole.System)

    def test_create_safe_without_active_payment_method(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice,
                                                      is_default=True)
        product = Product.objects.create(name="prodfoo", price=10)
        service = SafeService()
        with self.assertRaises(ValidationError):
            service.createSafe(alice, 'foosafe', 1, payment_method.pk, product.pk)

    def test_get_all_payments_for_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        PaymentMethod.objects.create(user=alice, is_default=True)
        PaymentMethod.objects.create(user=alice, is_default=False)
        payment_methods = PaymentMethodService("", "").getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(len(payment_methods), 2)

    def test_leave_participation(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method,
                                                     status=ParticipationStatus.Active)
        participation_service = ParticipationService()
        participation_service.leaveSafe(participation.pk, alice.pk)
        participation = Participation.objects.get(pk=participation.pk)
        self.assertEqual(participation.status, ParticipationStatus.Left)

    def test_leave_participation_status_error(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method,
                                                     status=ParticipationStatus.Pending)
        participation_service = ParticipationService()
        with self.assertRaises(ValidationError):
            participation_service.leaveSafe(participation.pk, alice.pk)

    def test_leave_participation_safe_status_error(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice, status=SafeStatus.Active)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method)
        participation_service = ParticipationService()
        with self.assertRaises(ValidationError):
            participation_service.leaveSafe(participation.pk, alice.pk)

    def test_leave_participation_for_other_users(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice, status=SafeStatus.Active)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method)
        participation_service = ParticipationService()
        with self.assertRaises(ValidationError):
            participation_service.leaveSafe(participation.pk, bob.pk)

    def test_participation_count(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        Participation.objects.create(user=alice,
                                     safe=safe,
                                     user_role=ParticipantRole.Initiator,
                                     payment_method=payment_method,
                                     status=ParticipationStatus.Active)
        participation_service = ParticipationService()
        total = participation_service.getParticipantCountForSafe(safe.pk)
        self.assertEqual(total, 1)

    @mock.patch('gocardless_pro.Client.redirect_flows')
    def test_create_payments_for_user(self, mock_gc):
        expected_dict = {
            "id": "foo",
            "redirect_url": "bar"
        }
        mock_gc.create.return_value = namedtuple("RedirectFlow", expected_dict.keys())(*expected_dict.values())
        payment_method_service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        pm1 = payment_method_service.createPaymentMethodForUser(user=alice, is_default=False, name="foopm",
                                                                pgw_description="desc", pgw_session_token="token",
                                                                pgw_success_redirect_url="url")
        self.assertEqual(pm1.is_default, True)
        self.assertEqual(pm1.gcflow.flow_id, 'foo')
        self.assertEqual(pm1.gcflow.flow_redirect_url, 'bar')
        pm2 = payment_method_service.createPaymentMethodForUser(user=alice, is_default=True, name="foopm",
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
            "confirmation_url": "bar"
        }
        mock_gc.complete.return_value = namedtuple("ConfirmationRedirectFlow", expected_complete_dict.keys())(
            *expected_complete_dict.values())
        expected_mandate_dict = {
            "id": "foo_mandate",
            "scheme": "bacs",
            "status": "created"
        }
        mock_gc_services.get.return_value = namedtuple("GCMandate", expected_mandate_dict.keys())(
            *expected_mandate_dict.values())
        payment_method_service = PaymentMethodService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method_service.createPaymentMethodForUser(user=alice, is_default=False, name="foopm",
                                                          pgw_description="desc", pgw_session_token="token",
                                                          pgw_success_redirect_url="url")
        payment_method_service.approveWithExternalSuccessWithFlowId(flow_id="foo")
        payment_methods = payment_method_service.getAllPaymentMethodsForUser(user=alice)
        self.assertEqual(payment_methods[0].status, PaymentMethodStatus.ExternalApprovalSuccessful)
        self.assertEqual(payment_methods[0].mandate.status, MandateStatus.Created)

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_create_payment(self, mock_ci):
        expected_dict = {
            "id": "foo",
            "status": "pending_submission",
            "charge_date": "2021-11-10"
        }
        mock_ci.create_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        mock_ci.get_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        payment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        mandate = Mandate.objects.create(mandate_external_id="foo_mandate")
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method)
        payment = payment_service.createPayment(participation.pk,
                                                10.0,
                                                'GBP',
                                                'description')
        self.assertEqual(payment.status, PaymentStatus.PendingSubmission)
        self.assertEqual(str(payment.amount), '£10.00')
        self.assertEqual(str(payment.charge_date), '2021-11-10')

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_create_cancelled_payment(self, mock_ci):
        expected_dict = {
            "id": "foo",
            "status": "cancelled",
            "charge_date": "2021-11-10"
        }
        mock_ci.create_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        mock_ci.get_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        payment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        mandate = Mandate.objects.create(mandate_external_id="foo_mandate")
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method)
        with self.assertRaises(ValidationError):
            payment_service.createPayment(participation.pk,
                                          10.0,
                                          'GBP',
                                          'description')

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_get_pending_payments(self, mock_ci):
        expected_dict = {
            "id": "foo",
            "status": "pending_submission",
            "charge_date": "2021-11-10"
        }
        mock_ci.create_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        mock_ci.get_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        payment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        alice_mandate = Mandate.objects.create(mandate_external_id="alice_mandate")
        alice_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=alice_mandate)
        bob_mandate = Mandate.objects.create(mandate_external_id="bob_mandate")
        bob_payment_method = PaymentMethod.objects.create(user=bob, is_default=True, mandate=bob_mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        alice_participation = Participation.objects.create(user=alice,
                                                           safe=safe,
                                                           user_role=ParticipantRole.Initiator,
                                                           payment_method=alice_payment_method)
        bob_participation = Participation.objects.create(user=bob,
                                                         safe=safe,
                                                         user_role=ParticipantRole.Participant,
                                                         payment_method=bob_payment_method)
        alice_payment = payment_service.createPayment(alice_participation.pk,
                                                      10.0,
                                                      'GBP',
                                                      'description')
        bob_payment = payment_service.createPayment(bob_participation.pk,
                                                    10.0,
                                                    'GBP',
                                                    'description')
        pending_payments = payment_service.getPendingConfirmationPaymentsForPayment(alice_payment.pk)
        self.assertEqual(len(pending_payments), 1)
        self.assertEqual(pending_payments[0].pk, bob_payment.pk)

    def test_payment_method_workflow(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        User.objects.create_user(email='bob@user.com', password='foo')
        mandate = Mandate.objects.create(mandate_external_id="foo_mandate")
        payment_method = PaymentMethod.objects.create(user=alice,
                                                      is_default=True,
                                                      mandate=mandate,
                                                      status=PaymentMethodStatus.ExternalApprovalSuccessful)
        service = PaymentMethodService()
        service.mandateExternallyCreated("foo_mandate")
        payment_method = PaymentMethod.objects.get(pk=payment_method.pk)
        self.assertEqual(payment_method.status, PaymentMethodStatus.ExternallyCreated)
        service.mandateExternallySubmitted("foo_mandate")
        payment_method = PaymentMethod.objects.get(pk=payment_method.pk)
        self.assertEqual(payment_method.status, PaymentMethodStatus.ExternallySubmitted)
        self.assertEqual(payment_method.mandate.status, MandateStatus.Submitted)
        service.mandateExternallyActivated("foo_mandate")
        payment_method = PaymentMethod.objects.get(pk=payment_method.pk)
        self.assertEqual(payment_method.status, PaymentMethodStatus.ExternallyActivated)

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_create_installment(self, mock_ci):
        expected_dict = {
            "id": "foo",
            "name": "safebar-installments",
        }
        mock_ci.create_instalment_with_schedule.return_value = namedtuple("GCInstalmentSchedule",
                                                                          expected_dict.keys())(
            *expected_dict.values())
        instalment_service = InstalmentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        instalment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        alice_mandate = Mandate.objects.create(mandate_external_id="alice_mandate")
        alice_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=alice_mandate)
        bob_mandate = Mandate.objects.create(mandate_external_id="bob_mandate")
        bob_payment_method = PaymentMethod.objects.create(user=bob, is_default=True, mandate=bob_mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=10, total_participants=2,
                                   initiator=alice)
        alice_participation = Participation.objects.create(user=alice,
                                                           safe=safe,
                                                           user_role=ParticipantRole.Initiator,
                                                           payment_method=alice_payment_method)
        bob_participation = Participation.objects.create(user=bob,
                                                         safe=safe,
                                                         user_role=ParticipantRole.Participant,
                                                         payment_method=bob_payment_method)
        instalments = instalment_service.createInstalmentForSafe(safe.pk, 10, 'GBP')
        self.assertEqual(len(instalments), 2)
        self.assertEqual(instalments[0].name, 'safebar-installments')
        saved_installments = Instalment.objects.filter(
            Q(participation=alice_participation.pk) |
            Q(participation=bob_participation.pk)).all()
        self.assertEqual(len(saved_installments), 2)

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_instalment_activated(self, mock_ci):
        expected_links = {
            "payments": ["foo_pay_1"]
        }
        expected_dict = {
            "id": "foo_instalment",
            "name": "safebar-instalments",
            "links": namedtuple("GCInstalmentSchedule", expected_links.keys())(*expected_links.values())
        }
        expected_payments_dict = {
            "id": "foo_pay_1",
            "amount": 1000,
            "currency": "GBP",
            "charge_date": "2021-11-22"
        }
        mock_ci.get_instalment.return_value = namedtuple("GCInstalmentSchedule",
                                                         expected_dict.keys())(*expected_dict.values())
        mock_ci.get_payment.return_value = namedtuple("GCPayments",
                                                      expected_payments_dict.keys())(*expected_payments_dict.values())
        instalment_service = InstalmentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        instalment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        alice_mandate = Mandate.objects.create(mandate_external_id="alice_mandate")
        alice_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=alice_mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=10, total_participants=2,
                                   initiator=alice)
        alice_participation = Participation.objects.create(user=alice,
                                                           safe=safe,
                                                           user_role=ParticipantRole.Initiator,
                                                           payment_method=alice_payment_method)
        instalment = Instalment.objects.create(external_id="foo_instalment",
                                               name="safebar-instalments",
                                               participation=alice_participation)
        instalment_service.instalmentActivated("foo_instalment")
        instalment = Instalment.objects.get(pk=instalment.pk)
        self.assertEqual(instalment.status, InstalmentStatus.Active)
        payment = Payment.objects.filter(external_id="foo_pay_1").first()
        self.assertEqual(payment.charge_date.strftime("%Y-%m-%d"), "2021-11-22")

    def test_safe_poke_payment_creation(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        alice_mandate = Mandate.objects.create(mandate_external_id="alice_mandate")
        alice_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=alice_mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=10, total_participants=2,
                                   initiator=alice, status=SafeStatus.Starting)
        alice_participation = Participation.objects.create(user=alice,
                                                           safe=safe,
                                                           user_role=ParticipantRole.Initiator,
                                                           payment_method=alice_payment_method)
        Payment.objects.create(external_id="foo_payment",
                               participation=alice_participation,
                               status=PaymentStatus.PendingSubmission,
                               amount=Money(10, 'GBP'))
        Instalment.objects.create(external_id="foo_instalment",
                                  name="safebar-instalments",
                                  participation=alice_participation,
                                  status=InstalmentStatus.Active)
        safe_service = SafeService()
        safe = safe_service.poke({'safe_id': safe.pk, 'type': PokeType.InstalmentActivated})
        self.assertIsNone(safe[1])
        self.assertEqual(safe[0].status, SafeStatus.Starting)

    def test_safe_start(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        Participation.objects.create(user=alice,
                                     safe=safe,
                                     user_role=ParticipantRole.Initiator,
                                     payment_method=payment_method)
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        PaymentMethod.objects.create(user=bob, is_default=True)
        service = InvitationService()
        invitation = service.createInvitation(alice, bob, safe)
        safe_service = SafeService()
        safe = safe_service.startSafe(alice, safe, True)
        self.assertEqual(safe.job.status, DoozezExecutableStatus.Created)
        self.assertEqual(safe.status, SafeStatus.Starting)
        invitation = Invitation.objects.get(pk=invitation.pk)
        self.assertEqual(invitation.status, InvitationStatus.RemovedBySender)

    def test_safe_start_with_non_initiator_user(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice,
                                                      is_default=True,
                                                      status=PaymentMethodStatus.ExternallyActivated)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice)
        Participation.objects.create(user=alice,
                                     safe=safe,
                                     user_role=ParticipantRole.Initiator,
                                     payment_method=payment_method)
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        safe_service = SafeService()
        with self.assertRaises(ValidationError):
            safe_service.startSafe(bob, safe, True)

    def test_task_service_run(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(safe_id):
            return safe_id

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        task = DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                         parameters='{"safe_id":1}', job=job, sequence=0)
        service = TaskService()
        result = service.runNextRunnableTask(job.pk)
        self.assertEqual(result.pk, task.pk)
        task = DoozezTask.objects.get(pk=task.pk)
        self.assertEqual(task.status, DoozezTaskStatus.Successful)

    def test_task_service_run_with_failure(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(safe_id):
            raise Exception('foo fail')

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"safe_id":1}', job=job, sequence=0)
        service = TaskService()
        with self.assertRaises(Exception):
            service.runNextRunnableTask(job.pk)
            task = DoozezTask.objects.get(pk=1)
            self.assertEqual(task.status, DoozezTaskStatus.Failed)
            self.assertIn('foo fail', task.exceptions)

    def test_task_sequence(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(sequence):
            return sequence

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":10}', job=job, sequence=10)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":15}', job=job, sequence=15)
        task = DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                         parameters='{"sequence":5}', job=job, sequence=5)
        service = TaskService()
        result = service.runNextRunnableTask(job.pk)
        self.assertEqual(result.pk, task.pk)

    def test_task_duplicate_sequence(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(sequence):
            return sequence

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.1}', job=job, sequence=0)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.2}', job=job, sequence=0)
        task = DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                         parameters='{"sequence":0.3}', job=job, sequence=0)
        service = TaskService()
        result = service.runNextRunnableTask(job.pk)
        self.assertEqual(result.pk, task.pk)

    def test_job_service_run(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        jobfoo = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        jobbar = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        service = JobService()
        service.runNextExecutable()
        post_jobbar = DoozezJob.objects.get(pk=jobbar.pk)
        self.assertEqual(post_jobbar.status, DoozezExecutableStatus.Running)
        post_jobfoo = DoozezJob.objects.get(pk=jobfoo.pk)
        self.assertEqual(post_jobfoo.status, DoozezExecutableStatus.Created)

    def test_job_executor_execute(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(safe_id):
            raise Exception('foo fail')

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"safe_id":1}', job=job, sequence=0)
        executor = JobExecutor()
        executor.executeNextRunnableJob()
        job = DoozezJob.objects.get(pk=job.pk)
        self.assertEqual(job.status, DoozezExecutableStatus.Failed)

    def test_task_service_create_task(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_draw(sequence):
            return sequence

        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        service = TaskService()
        task = service.createTaskForJob(DoozezTaskType.Draw, '{"sequence":0.1}', 15, job)
        result = DoozezTask.objects.get(pk=task.pk)
        self.assertEqual(result.parameters, '{"sequence":0.1}')

    def test_task_planner_start_safe_tasks(self):
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice,
                                                      is_default=True,
                                                      status=PaymentMethodStatus.ExternallyActivated)
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        joe = self.User.objects.create_user(email='joe@user.com', password='foo')
        bob_payment_method = PaymentMethod.objects.create(user=bob,
                                                          is_default=True,
                                                          status=PaymentMethodStatus.ExternallyActivated)
        joe_payment_method = PaymentMethod.objects.create(user=joe,
                                                          is_default=True,
                                                          status=PaymentMethodStatus.ExternallyActivated)
        product = Product.objects.create(name="prodfoo", price=10)
        safe_service = SafeService()
        safe = safe_service.createSafe(alice, 'safebar', 10, payment_method.pk, product.pk)
        participation = Participation.objects.create(user=bob,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Participant,
                                                     payment_method=bob_payment_method)
        Participation.objects.create(user=joe,
                                     safe=safe,
                                     user_role=ParticipantRole.Participant,
                                     payment_method=joe_payment_method,
                                     status=ParticipationStatus.Left)
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        planner = TaskPlanner()
        result = planner.createTasksForStartSafe(safe, job)
        self.assertEqual(len(result), 4)
        task = DoozezTask.objects.get(pk=result[2].pk)
        self.assertEqual(task.task_type, DoozezTaskType.CreatePayment)
        self.assertEqual(task.sequence, 2)
        self.assertEqual(
            task.parameters,
            '{{"participation_id":"{}", "amount":"10", "currency":"GBP"}}'.format(participation.pk))

    def test_event_executor(self):
        service = EventService()
        event = service.createEvent('foo_event',
                                    '17-10-2021', 'mandates',
                                    'active', 'foo_mandate',
                                    'cause', 'description')
        executor = EventExecutor()

        def mandate_active(link_id):
            return link_id

        executor.mandate_active = mandate_active
        link_id = executor.executeNextRunnableJob()
        self.assertEqual(link_id, 'foo_mandate')
        event = Event.objects.get(pk=event.pk)
        self.assertEqual(event.status, DoozezExecutableStatus.Successful)

    @mock.patch('safe.client_interfaces.PaymentGatewayClient')
    def test_payment_confirmed(self, mock_ci):
        expected_dict = {
            "id": "foo",
            "status": "pending_submission",
            "charge_date": "2021-11-10"
        }
        mock_ci.create_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        mock_ci.get_payment.return_value = namedtuple("GCPayment", expected_dict.keys())(
            *expected_dict.values())
        payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        payment_service.payment_gate_way_client = mock_ci
        alice = self.User.objects.create_user(email='alice@user.com', password='foo')
        bob = self.User.objects.create_user(email='bob@user.com', password='foo')
        alice_mandate = Mandate.objects.create(mandate_external_id="alice_mandate")
        alice_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=alice_mandate)
        bob_mandate = Mandate.objects.create(mandate_external_id="bob_mandate")
        bob_payment_method = PaymentMethod.objects.create(user=alice, is_default=True, mandate=bob_mandate)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice, status=SafeStatus.Starting)
        alice_participation = Participation.objects.create(user=alice,
                                                           safe=safe,
                                                           user_role=ParticipantRole.Initiator,
                                                           payment_method=alice_payment_method)
        bob_participation = Participation.objects.create(user=bob,
                                                         safe=safe,
                                                         user_role=ParticipantRole.Participant,
                                                         payment_method=bob_payment_method)
        alice_payment = payment_service.createPayment(alice_participation.pk,
                                                      10.0,
                                                      'GBP',
                                                      'description')
        bob_payment = payment_service.createPayment(bob_participation.pk,
                                                    10.0,
                                                    'GBP',
                                                    'description')
        executor = EventExecutor()
        payment = executor.payment_confirmed(alice_payment.pk)
        self.assertEqual(payment.id, alice_payment.pk)
        safe = Safe.objects.get(pk=safe.pk)
        self.assertEqual(safe.status, SafeStatus.Starting)
        executor.payment_confirmed(bob_payment.pk)
        safe = Safe.objects.get(pk=safe.pk)
        self.assertEqual(safe.status, SafeStatus.Started)

    def test_render_template(self):
        result = utils.render_template_with_context('notification/invite.txt', {'user': 'foo', 'safe': 'bar'})
        expected = "foo has invited you to bar"
        self.assertEqual(expected, result)

    def test_send_notification(self):
        class MockedDevice(object):

            def send_message(self, message):
                return message

        notification_provider = utils.notification_provider
        mock_service = create_autospec(NotificationProvider)
        mock_service.getDevicesForUser.return_value = MockedDevice()
        utils.notification_provider = mock_service
        result = utils.send_notification_to_user_from_template(1, 'title', 'notification/invite.txt', '',
                                                               {'user': 'foo', 'safe': 'bar'})
        expected = "foo has invited you to bar"
        self.assertEqual(expected, result.notification.body)
        utils.notification_provider = notification_provider
