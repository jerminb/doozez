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

    @mock.patch('gocardless_pro.Client')
    def test_create_flow(self, mock_gc):
        mock_gc.redirect_flows.create.return_value = {
            "id": "foo"
        }
        dict = {
            "first_name": "alice",
            "last_name": "bob",
            "email": "alice@test.com"
        }
        user = namedtuple("User", dict.keys())(*dict.values())
        gate_way = PaymentGatewayClient(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        self.assertIsNotNone(gate_way.create_approval_flow("desc", "token", "url", user))
