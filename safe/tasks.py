import os
import random

from rest_framework.exceptions import ValidationError

from .decorators import doozez_task
from .models import DoozezTaskType, PaymentMethodStatus
from .services import ParticipationService, PaymentService

participation_service = ParticipationService()
payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], os.environ['GC_ENVIRONMENT'])


def draw(safe_id, parti_service):
    participations = parti_service.getParticipationForSafe(safe_id)
    if participations is None:
        raise IndexError("no participation found")
    random.shuffle(participations)
    for i in range(len(participations)):
        if participations[i].payment_method.status != PaymentMethodStatus.ExternalApprovalSuccessful:
            raise ValidationError("payment-method is not approved yet")
        participations[i].win_sequence = i
        participations[i].save()
    return participations


def create_payment_for_participant(participation_id, amount, currency, pay_service):
    return pay_service.createPayment(participation_id, amount, currency, '')


@doozez_task(type=DoozezTaskType.Draw)
def task_draw(safe_id):
    draw(safe_id, participation_service)


@doozez_task(type=DoozezTaskType.CreatePayment)
def task_create_payment_for_participant(participation_id, amount, currency):
    create_payment_for_participant(participation_id, amount, currency, payment_service)
