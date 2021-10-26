"""doozez URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls import url
from django.urls import path, include
from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

from allauth.account.views import confirm_email
from safe.views import ConfirmatioView, PasswordResetView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('v1/', include('safe.urls')),
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^auth/registration/', include('rest_auth.registration.urls')),
    url(r'^account/', include('allauth.urls')),
    url(r'^accounts/registration/account-confirm-email/(?P<key>.+)/$', confirm_email, name='account_confirm_email'),
    url(r'^auth/password_reset/', include('django_rest_passwordreset.urls', namespace='password_reset')),
    url(r'^auth/password_reset_confirm/', PasswordResetView.as_view(), name='password_reset_confirm'),
    url('confirmation', ConfirmatioView.as_view(), name='confirmation'),
    path('devices', FCMDeviceAuthorizedViewSet.as_view({'post': 'create'}), name='create_fcm_device'),
]
