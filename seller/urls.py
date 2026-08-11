from django.urls import path, include
from rest_framework.routers import DefaultRouter
from seller.views import ShopViewSet, ShopDeliverySettingViewSet, SellerRequestViewSet

router = DefaultRouter()

router.register(r'shops', ShopViewSet, basename='shop')
router.register(
    r'seller-requests',
    SellerRequestViewSet,
    basename='seller-request',
)

urlpatterns = [
    path('', include(router.urls)),
    path(
            "shops/<int:shop_pk>/delivery-settings/",
            ShopDeliverySettingViewSet.as_view(
                {
                    "get": "list",
                    "post": "create",
                    "delete": "destroy",
                }
            ),
            name="shop-delivery-settings",
        ),
]


