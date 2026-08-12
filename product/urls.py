from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, UniqueProductViewSet, CartView, CartItemCreateView, CartItemDetailView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register( r"unique-products", UniqueProductViewSet, basename="unique-product", )

urlpatterns = [
    path('', include(router.urls)),
    path(
            "cart/",
            CartView.as_view(),
            name="cart",
        ),

        path(
            "cart/items/",
            CartItemCreateView.as_view(),
            name="cart-item-create",
        ),

        path(
            "cart/items/<int:pk>/",
            CartItemDetailView.as_view(),
            name="cart-item-detail",
        ),
]
