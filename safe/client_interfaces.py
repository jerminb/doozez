from django.core.exceptions import ValidationError
import gocardless_pro

from . import utils


class GCInstalmentSchedule(object):
    id = ""
    created_at = ""
    name = ""
    status = ""
    total_amount = ""
    currency = ""
    mandate = ""
    idempotency_key = ""
    payment_errors = []
    payments = []

    def __init__(self, id, created_at, name, status, total_amount, currency, mandate, idempotency_key=""):
        self.id = id
        self.created_at = created_at
        self.name = name
        self.status = status
        self.total_amount = total_amount
        self.currency = currency
        self.mandate = mandate
        self.idempotency_key = idempotency_key


class GCPayment(object):
    id = ""
    created_at = ""
    status = ""
    amount = ""
    currency = ""
    mandate = ""
    charge_date = ""
    idempotency_key = ""

    def __init__(self, id, created_at, status, amount, currency, mandate, charge_date="", idempotency_key=""):
        self.id = id
        self.created_at = created_at
        self.status = status
        self.amount = amount
        self.currency = currency
        self.mandate = mandate
        self.charge_date = charge_date
        self.idempotency_key = idempotency_key


class GCMandate(object):
    id = ""
    scheme = ""
    status = ""

    def __init__(self, id, scheme, status):
        self.id = id
        self.scheme = scheme
        self.status = status


class ConfirmationRedirectFlow(object):
    mandate_id = ""
    customer_id = ""
    confirmation_url = ""

    def __init__(self, mandate_id, customer_id, confirmation_url):
        self.mandate_id = mandate_id
        self.customer_id = customer_id
        self.confirmation_url = confirmation_url


class RedirectFlow(object):
    redirect_id = ""
    redirect_url = ""

    def __init__(self, redirect_id, redirect_url):
        self.redirect_id = redirect_id
        self.redirect_url = redirect_url


class PaymentGatewayClient(object):
    client = None
    access_token = ""
    environment = ""

    def __init__(self, access_token, environment):
        self.access_token = access_token
        self.environment = environment

    def __build_client(self):
        self.client = gocardless_pro.Client(
            # We recommend storing your access token in an
            # environment variable for security
            access_token=self.access_token,
            # Change this to 'live' when you are ready to go live.
            environment=self.environment
        )
        return self.client

    def get_client(self):
        if self.client is None:
            return self.__build_client()
        else:
            return self.client

    def create_approval_flow(self, description, session_token, success_redirect_url, user):
        redirect_flow = self.get_client().redirect_flows.create(
            params={
                "description": description,  # This will be shown on the payment pages
                "session_token": session_token,
                "success_redirect_url": success_redirect_url,
                "prefilled_customer": {  # Optionally, prefill customer details on the payment page
                    "given_name": user.first_name,
                    "family_name": user.last_name,
                    "email": user.email,
                }
            }
        )
        return RedirectFlow(redirect_flow.id, redirect_flow.redirect_url)

    def complete_approval_flow(self, flow_id, session_token):
        redirect_flow = self.get_client().redirect_flows.complete(
            flow_id,
            params={
                "session_token": session_token
            })
        return ConfirmationRedirectFlow(redirect_flow.links.mandate, redirect_flow.links.customer,
                                        redirect_flow.confirmation_url)

    def get_mandate(self, mandate_id):
        if mandate_id is None or mandate_id == "":
            raise ValidationError("mandate id can not be empty")
        mandate = self.get_client().mandates.get(mandate_id)
        if mandate is None:
            return None
        return GCMandate(mandate_id, mandate.scheme, mandate.status)

    def create_payment(self, mandate_id, amount, currency="GBP"):
        idempotency_key = utils.id_generator()
        gc_amount = int(float(amount))
        payment = self.get_client().payments.create(
            params={
                "amount": gc_amount,  # amount in pence
                "currency": currency,
                "links": {
                    "mandate": mandate_id
                },
                "metadata": {
                    # Almost all resources in the API let you store custom metadata,
                    # which you can retrieve later
                }
            }, headers={
                'Idempotency-Key': idempotency_key,
            })

        return GCPayment(id=payment.id, created_at=payment.created_at, status=payment.status, amount=payment.amount,
                         currency=payment.currency,
                         mandate=payment.links.mandate, charge_date=payment.charge_date,
                         idempotency_key=idempotency_key)

    def get_payment(self, payment_id):
        payment = self.get_client().payments.get(payment_id)
        return GCPayment(id=payment.id, created_at=payment.created_at, status=payment.status, amount=payment.amount,
                         currency=payment.currency,
                         mandate=payment.links.mandate, charge_date=payment.charge_date)

    def create_installment_with_schedule(self, name, mandate_id, total_amount, app_fee, amounts,
                                         currency, start_date, interval, interval_unit='monthly'):
        idempotency_key = utils.id_generator()
        instalment_schedule = self.get_client().instalment_schedules.create_with_schedule(
            params={
                "name": name,
                "total_amount": total_amount,  # total amount in pence
                "app_fee": app_fee,
                "currency": currency,
                "instalments": {
                    "start_date": start_date,
                    "interval_unit": interval_unit,
                    "interval": interval,
                    "amounts": amounts
                },
                "links": {
                    "mandate": mandate_id
                },
                "metadata": {}
            }, headers={
                "Idempotency-Key": idempotency_key
            }
        )
        return GCInstalmentSchedule(id=instalment_schedule.id, created_at=instalment_schedule.created_at,
                                    name=instalment_schedule.name, status=instalment_schedule.status,
                                    total_amount=instalment_schedule.amount,
                                    currency=instalment_schedule.currency, mandate=instalment_schedule.links.mandate,
                                    idempotency_key=idempotency_key)
