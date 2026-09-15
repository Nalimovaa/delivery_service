from django.urls import path, include
from rest_framework.routers import DefaultRouter
from seller.views import ShopViewSet, CDEKShopDeliverySettingViewSet, SellerRequestViewSet, ReturnRequestShopListView, \
    ReturnRequestShopDetailView

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
            CDEKShopDeliverySettingViewSet.as_view(
                {
                    "get": "list",
                    "post": "create",
                    "delete": "destroy",
                }
            ),
            name="shop-delivery-settings",
        ),
    path(
            "return-requests/shop/",
            ReturnRequestShopListView.as_view(),
            name="return-request-shop-list",
        ),
    path(
            "return-requests/shop/<int:pk>/",
            ReturnRequestShopDetailView.as_view(),
            name="return-request-shop-detail",
        ),

]


