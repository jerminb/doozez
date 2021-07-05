from rest_framework.fields import empty
from rest_framework import serializers


class NullableJSONField(serializers.JSONField):

    def get_value(self, dictionary):
        result = super().get_value(dictionary)
        if result is empty:
            return None
        return result