from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delivery.views import CDEKTariffViewSet, DeliveryPreCalculationViewSet, DeliveryCalculationViewSet, \
    DeliveryPointsViewSet, CdekWebhookOrderStatusView, CDEKDeliveryDeleteView
from order.views import CDEKClientReturnCreateView

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

router.register(
    r"delivery/calculate",
    DeliveryCalculationViewSet,
    basename="delivery-calculate",
)

router.register(
    r"delivery/points",
    DeliveryPointsViewSet,
    basename="delivery-points",
)

urlpatterns = [
    path('', include(router.urls)),
    path(
            "delivery/webhooks/cdek/order-status/",
            CdekWebhookOrderStatusView.as_view(),
            name="cdek-webhook-order-status",
        ),
    path(
        "delivery/cdek/delete/",
        CDEKDeliveryDeleteView.as_view(),
        name="cdek-delivery-delete",
    ),
    path(
        "return-requests/<int:pk>/cdek-return/",
        CDEKClientReturnCreateView.as_view(),
        name="return-request-cdek-return",
    ),
]