from django.urls import include, path
from rest_framework import routers
from . import views

token_detail = views.TokensViewSet.as_view({
    'get': 'get_user_for_token',
})

router = routers.DefaultRouter()
router.register(r'safes', views.SafeViewSet)
router.register(r'users', views.UserViewSet, basename="doozezuser")
router.register(r'groups', views.GroupViewSet)
router.register(r'invitations', views.InvitationViewSet, basename="invitation")
router.register(r'products', views.ProductViewSet, basename="product")
router.register(r'participations', views.ParticipationViewSet, basename="participation")
router.register(r'payment-methods', views.PaymentMethodViewSet, basename="paymentmethod")
router.register(r'payments', views.PaymentViewSet, basename="payment")
router.register(r'jobs', views.JobsViewSet, basename="job")
router.register(r'webhooks', views.WebhookViewSet, basename="webhook")

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('tokens/user/', token_detail, name='tokens-user-detail'),
]
