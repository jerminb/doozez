from collections import namedtuple

from django.test import TestCase
import os
from unittest import mock

from .client_interfaces import PaymentGatewayClient


class InterfaceTest(TestCase):
    def setUp(self):
        pass

    def test_build_client(self):
        gate_way = PaymentGatewayClient(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        self.assertIsNotNone(gate_way.get_client())

    @mock.patch('gocardless_pro.Client.redirect_flows')
    def test_create_flow(self, mock_gc):
        expected_dict = {
            "id": "foo",
            "redirect_url": "bar"
        }
        mock_gc.create.return_value = namedtuple("RedirectFlow", expected_dict.keys())(*expected_dict.values())
        user_dict = {
            "first_name": "alice",
            "last_name": "bob",
            "email": "alice@test.com"
        }
        user = namedtuple("User", user_dict.keys())(*user_dict.values())
        gate_way = PaymentGatewayClient(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        result = gate_way.create_approval_flow("desc", "token", "url", user)
        self.assertEqual(result.redirect_id, "foo")
