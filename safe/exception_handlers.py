from django.http import HttpResponse
from django.conf import settings
import traceback


class ErrorHandlerMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if not settings.DEBUG:
            if exception:
                message = "{url}\n{error}\n{tb}".format(
                    url=request.build_absolute_uri(),
                    error=repr(exception),
                    tb=traceback.format_exc()
                )
                # Do whatever with the message now
            return HttpResponse(message, status=500)