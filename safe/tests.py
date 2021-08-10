import json
from collections import namedtuple
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import Safe, Invitation, InvitationStatus, PaymentMethod, DoozezJob, DoozezJobType, DoozezTaskStatus, \
    DoozezTaskType, DoozezTask, Participation, ParticipantRole, SafeStatus, ParticipationStatus


class UsersManagersTests(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(email='normal@user.com', password='foo')
        self.assertEqual(user.email, 'normal@user.com')
        self.assertFalse(user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email='')
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password="foo")

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(email='super@user.com', password='foo')
        self.assertEqual(admin_user.email, 'super@user.com')
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email='super@user.com', password='foo', is_superuser=False)

    def test_post_invitations_for_user(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1, initiator=alice)
        data = {
            'recipient': bob.pk,
            'safe': safe.pk
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('invitation-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'Pending')

    def test_get_invitations_for_recipient(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        tom = User.objects.create_user(email='tom@user.com', password='foo')
        safebob = Safe.objects.create(name='safebob', monthly_payment=1, total_participants=1)
        safetom = Safe.objects.create(name='safetom', monthly_payment=1, total_participants=1)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob, safe=safebob)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=bob, recipient=tom, safe=safetom)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('invitation-list'),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_get_invitations_for_sender_recipient(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        safebob = Safe.objects.create(name='safebob', monthly_payment=1, total_participants=1)
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob, safe=safebob)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=bob, recipient=alice, safe=safealice)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('invitation-list'),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_invitation_for_safe_id(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        safebob = Safe.objects.create(name='safebob', monthly_payment=1, total_participants=1, initiator=bob)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob, safe=safealice)
        Invitation.objects.create(status=InvitationStatus.Pending, sender=bob, recipient=alice, safe=safebob)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('invitation-list') + "?safe=1",
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['recipient']['email'], 'bob@user.com')
        self.assertEqual(response.data[0]['id'], 1)

    def test_accept_invitation(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        invitation = Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob,
                                               safe=safealice)
        bob_payment_method = PaymentMethod.objects.create(user=bob, is_default=True)
        data = {
            'action': 'ACCEPT',
            'json_data': '{"payment_method_id":' + str(bob_payment_method.pk) + '}'
        }
        client = APIClient()
        client.login(username='bob@user.com', password='foo')
        response = client.patch(reverse('invitation-detail', args=[invitation.pk]),
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Accepted')

    def test_accept_invitation_with_no_data(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        invitation = Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob,
                                               safe=safealice)
        data = {
            'action': 'ACCEPT'
        }
        client = APIClient()
        client.login(username='bob@user.com', password='foo')
        response = client.patch(reverse('invitation-detail', args=[invitation.pk]),
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_remove_invitation_with_recipeint(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        invitation = Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob,
                                               safe=safealice)
        data = {
            'action': 'REMOVE'
        }
        client = APIClient()
        client.login(username='bob@user.com', password='foo')
        response = client.patch(reverse('invitation-detail', args=[invitation.pk]),
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_decline_invitation(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        bob = User.objects.create_user(email='bob@user.com', password='foo')
        invitation = Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob,
                                               safe=safealice)
        PaymentMethod.objects.create(user=bob, is_default=True)
        data = {
            'action': 'DECLINE',
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.patch(reverse('invitation-detail', args=[invitation.pk]),
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'Declined')

    def test_post_safe_for_user(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        User.objects.create_user(email='bob@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        data = {
            'name': 'foosafe',
            'monthly_payment': '2',
            'payment_method_id': payment_method.pk
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('safe-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PPT')
        response = client.get(reverse('participation-detail', args=[2]),
                              content_type='application/json')
        self.assertEqual(response.data['user']['email'], "alice@user.com")
        self.assertEqual(response.data['payment_method']['is_default'], True)
        response = client.get(reverse('participation-list') + "?safe=1",
                              content_type='application/json')
        self.assertEqual(response.data[1]['user']['email'], "alice@user.com")

    def test_get_safe_for_participant(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        User.objects.create_user(email='bob@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        data = {
            'name': 'foosafe',
            'monthly_payment': '2',
            'payment_method_id': payment_method.pk
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('safe-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        client.login(username='bob@user.com', password='foo')
        response = client.get(reverse('safe-list'),
                              content_type='application/json')
        self.assertEqual(len(response.data), 0)

    def test_retrieve_participation_for_other_user(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        User.objects.create_user(email='bob@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        data = {
            'name': 'foosafe',
            'monthly_payment': '2',
            'payment_method_id': payment_method.pk
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('safe-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        client.login(username='bob@user.com', password='foo')
        response = client.get(reverse('participation-detail', args=[1]),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_payment_method_for_other_user(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        User.objects.create_user(email='bob@user.com', password='foo')
        PaymentMethod.objects.create(user=alice, is_default=True)
        client = APIClient()
        client.login(username='bob@user.com', password='foo')
        response = client.get(reverse('paymentmethod-list'),
                              content_type='application/json')
        self.assertEqual(len(response.data), 0)

    def test_post_participants(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('participation-list'),
                               data=json.dumps({}),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_leave_participants(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        safe = Safe.objects.create(name='safebar', monthly_payment=1, total_participants=1,
                                   initiator=alice, status=SafeStatus.PendingParticipants)
        participation = Participation.objects.create(user=alice,
                                                     safe=safe,
                                                     user_role=ParticipantRole.Initiator,
                                                     payment_method=payment_method,
                                                     status=ParticipationStatus.Active)
        data = {
            'action': 'LEAVE',
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.patch(reverse('participation-detail', args=[participation.pk]),
                                data=json.dumps(data),
                                content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], ParticipationStatus.Left.name)

    def test_get_safe_details_with_id(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        # safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        payment_method = PaymentMethod.objects.create(user=alice, is_default=True)
        data = {
            'name': 'foosafe',
            'monthly_payment': '2',
            'payment_method_id': payment_method.pk
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('safe-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        response = client.get(reverse('safe-detail', args=[response.data['id']]),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], 1)

    # def test_post_payment_methods(self):
    #     User = get_user_model()
    #     User.objects.create_user(email='alice@user.com', first_name='alice', last_name='bob', password='foo')
    #     data = {
    #         'is_default': False
    #     }
    #     client = APIClient()
    #     client.login(username='alice@user.com', password='foo')
    #     response = client.post(reverse('paymentmethod-list'),
    #                            data=json.dumps(data),
    #                            content_type='application/json')
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data['is_default'], True)

    def test_get_jobs_with_id(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.1}', job=job, sequence=0)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.2}', job=job, sequence=0)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('job-detail', args=[job.pk]),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['jobs_tasks']), 2)

    def test_get_jobs_with_task_status(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        job = DoozezJob.objects.create(job_type=DoozezJobType.StartSafe, user=alice)
        DoozezTask.objects.create(status=DoozezTaskStatus.Failed, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.1}', job=job, sequence=0)
        DoozezTask.objects.create(status=DoozezTaskStatus.Pending, task_type=DoozezTaskType.Draw,
                                  parameters='{"sequence":0.2}', job=job, sequence=0)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('job-get-with-task-status', args=[job.pk]) + "?status=FLD",
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['jobs_tasks']), 1)

    def test_get_user_with_token(self):
        User = get_user_model()
        User.objects.create_user(email='alice@user.com', password='foo')
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('tokens-user-detail', args=[]),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'alice@user.com')
