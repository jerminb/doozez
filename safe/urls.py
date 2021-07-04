from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'safes', views.SafeViewSet)
router.register(r'users', views.UserViewSet, basename="doozezuser")
router.register(r'groups', views.GroupViewSet)
router.register(r'invitations', views.InvitationViewSet, basename="invitation")
router.register(r'participation', views.ParticipationViewSet, basename="participation")
router.register(r'payment-methods', views.PaymentMethodViewSet, basename="paymentmethod")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework'))
]