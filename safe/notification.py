from fcm_django.models import FCMDevice


class NotificationService(object):
    def __init__(self):
        pass

    def getDevicesForUser(self, user_id):
        return FCMDevice.objects.filter(user=user_id).last()
