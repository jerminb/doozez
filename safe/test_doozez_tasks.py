from collections import namedtuple
from unittest import mock
from unittest.mock import create_autospec

from django.test import TestCase
from .decorators import doozez_task, run, clear
from .models import DoozezTaskType, PaymentMethodStatus
from .services import ParticipationService
from .tasks import draw


class DoozezTaslTest(TestCase):

    def test_decorator(self):
        clear()

        @doozez_task(type=DoozezTaskType.Draw)
        def test_func(dummy):
            return dummy

        result = run(type=DoozezTaskType.Draw.value, dummy="foo")
        self.assertEqual(result, "foo")

    def test_draw(self):
        clear()

        class MockedPaymentMethod(object):
            status = PaymentMethodStatus.ExternalApprovalSuccessful

        class MockedParticipation(object):
            win_sequence = -1
            payment_method = MockedPaymentMethod()

            def save(self):
                pass
        mock_service = create_autospec(ParticipationService)
        expected_participations = [MockedParticipation() for i in range(10)]
        mock_service.getParticipationForSafe.return_value = expected_participations
        participations = draw(safe_id=1, participation_service=mock_service)
        self.assertGreater(participations[5].win_sequence, 0)
