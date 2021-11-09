import random
import string
import traceback

from django import template
from django.core.exceptions import ValidationError
from firebase_admin.messaging import Notification, Message

from .notification import NotificationProvider

notification_provider = NotificationProvider()


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def exception_as_dict(ex, err):
    exc_type, exc_val, tb = err
    tb = ''.join(traceback.format_exception(
        exc_type,
        exc_val if isinstance(exc_val, exc_type) else exc_type(exc_val),
        tb
    ))
    return dict(type=ex.__class__.__name__,
                message=str(ex),
                traceback=tb)


def render_template_with_context(template_path, context):
    t = template.loader.get_template(template_path)
    return t.render(context)


def send_notification_to_user_from_template(user_id, title, template_path, image, context):
    message = render_template_with_context(template_path, context)
    return send_notification_to_user(user_id, title, message, image)


def send_notification_to_user(user_id, title, message, image):
    device = notification_provider.getDevicesForUser(user_id)
    if device is None:
        raise ValidationError("no device found for user_id {}".format(user_id))
    result = device.send_message(Message(
        notification=Notification(title=title, body=message, image=image)
    ))
    return result
