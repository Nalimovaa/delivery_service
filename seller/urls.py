from django.urls import path, include
from rest_framework.routers import DefaultRouter
from seller.views import ShopViewSet, ShopDeliverySettingViewSet

router = DefaultRouter()

router.register(r'shops', ShopViewSet, basename='shop')

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


