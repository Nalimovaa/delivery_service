from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delivery.views import CDEKTariffViewSet, DeliveryPreCalculationViewSet

router = DefaultRouter()


router.register(
    r'alltariffs',
    CDEKTariffViewSet,
    basename="cdek-tariffs",
)

router.register(
    r"delivery/pre-calculate",
    DeliveryPreCalculationViewSet,
    basename="delivery-pre-calculate",
)

urlpatterns = [
    path('', include(router.urls)),
]