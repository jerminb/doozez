import gocardless_pro


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
        return redirect_flow.confirmation_url
