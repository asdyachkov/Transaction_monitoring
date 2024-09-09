from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from account.views import UserViewSet, UserProfileViewSet, AccountViewSet
from clickhouse.views import get_analytics
from currency.views import CurrencyViewSet
from transaction.views import TransactionViewSet
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'account-profiles', UserProfileViewSet)
router.register(r'currencies', CurrencyViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'transactions', TransactionViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('analytics/', get_analytics, name='get_analytics')
]

