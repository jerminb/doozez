import os
import random

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from .decorators import doozez_task
from .models import DoozezTaskType, PaymentMethodStatus, ParticipantRole
from .services import ParticipationService, PaymentService, InstallmentService

participation_service = ParticipationService()
payment_service = PaymentService(os.environ['GC_ACCESS_TOKEN'], os.environ['GC_ENVIRONMENT'])
installment_service = InstallmentService(os.environ['GC_ACCESS_TOKEN'], os.environ['GC_ENVIRONMENT'])


def draw(safe_id, parti_service):
    system_participation = parti_service.getSystemParticipation(safe_id)
    if system_participation is None:
        raise ValidationError("system participation not found")
    system_participation.win_sequence = 0
    system_participation.save()
    participations = list(parti_service.getNonSystemParticipation(safe_id))
    if participations is None:
        raise IndexError("no participation found")
    random.shuffle(participations)
    for i in range(len(participations)):
        if participations[i].payment_method.status != PaymentMethodStatus.ExternallyActivated:
            raise ValidationError("payment-method {} is not approved yet".format(participations[i].payment_method.pk))
        participations[i].win_sequence = i + 1
        participations[i].save()
    return [system_participation, *participations]


def create_payment_for_participant(participation_id, amount, currency, pay_service):
    return pay_service.createPayment(participation_id, amount, currency, '')


def create_payment_for_installments(safe_id, app_fee, currency, installment_service):
    return installment_service.createInstallmentForSafe(safe_id, app_fee, currency)


def add_tasks():
    @doozez_task(type=DoozezTaskType.Draw)
    def task_draw(safe_id):
        draw(safe_id, participation_service)

    @doozez_task(type=DoozezTaskType.CreatePayment)
    def task_create_payment_for_participant(participation_id, amount, currency):
        create_payment_for_participant(participation_id, amount, currency, payment_service)

    @doozez_task(type=DoozezTaskType.CreateInstallments)
    def task_create_installments_for_safe(safe_id, app_fee, currency):
        create_payment_for_installments(safe_id, app_fee, currency, installment_service)

    return



