import json
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient
from rest_framework import status

from .models import Safe, Invitation, InvitationStatus


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
        self.assertEqual(response.data['status'], 'PND')

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
        invitation = Invitation.objects.create(status=InvitationStatus.Pending, sender=alice, recipient=bob, safe=safealice)
        data = {
            'action': 'accept'
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.patch(reverse('invitation-detail', args=[invitation.pk]),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_post_safe_for_user(self):
        User = get_user_model()
        User.objects.create_user(email='alice@user.com', password='foo')
        data = {
            'name': 'foosafe',
            'monthly_payment': '2'
        }
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.post(reverse('safe-list'),
                               data=json.dumps(data),
                               content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'PPT')

    def test_get_safe_details_with_id(self):
        User = get_user_model()
        alice = User.objects.create_user(email='alice@user.com', password='foo')
        safealice = Safe.objects.create(name='safealice', monthly_payment=1, total_participants=1, initiator=alice)
        client = APIClient()
        client.login(username='alice@user.com', password='foo')
        response = client.get(reverse('safe-detail', args=[safealice.pk]),
                              content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], 1)
