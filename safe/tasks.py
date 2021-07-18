import random

from rest_framework.exceptions import ValidationError

from .decorators import doozez_task
from .models import DoozezTaskType, PaymentMethodStatus
from .services import ParticipationService


def draw(safe_id, participation_service):
    participations = participation_service.getParticipationForSafe(safe_id)
    if participations is None:
        raise IndexError("no participation found")
    random.shuffle(participations)
    for i in range(len(participations)):
        if participations[i].payment_method.status != PaymentMethodStatus.ExternalApprovalSuccessful:
            raise ValidationError("payment-method is not approved yet")
        participations[i].win_sequence = i
        participations[i].save()
    return participations


def withdraw_first_payment(safe_id, participation_service):
    pass


@doozez_task(type=DoozezTaskType.Draw)
def task_draw(safe_id):
    participation_service = ParticipationService()
    draw(safe_id, participation_service)
