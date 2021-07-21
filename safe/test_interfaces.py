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

    @mock.patch('gocardless_pro.Client.payments')
    def test_create_payment(self, mock_gc):
        expected_link_dict = {
            "mandate": "foo_mandate"
        }
        expected_link = namedtuple("PaymentLinks", expected_link_dict.keys())(
            *expected_link_dict.values())
        expected_dict = {
            "id": "foo",
            "created_at": "2021-07-18T15:39:32.145Z",
            "status": "pending_submission",
            "amount": 1000,
            "currency": "GBP",
            "links": expected_link,
            "charge_date": "2021-07-23",
            "idempotency_key": ""
        }
        mock_gc.create.return_value = namedtuple("Payment", expected_dict.keys())(*expected_dict.values())
        gate_way = PaymentGatewayClient(os.environ['GC_ACCESS_TOKEN'], 'sandbox')
        result = gate_way.create_payment(mandate_id="foo_mandate", amount=1000)
        self.assertEqual(result.currency, "GBP")
        self.assertEqual(result.amount, 1000)
