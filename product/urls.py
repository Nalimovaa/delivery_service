from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, UniqueProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register( r"unique-products", UniqueProductViewSet, basename="unique-product", )

urlpatterns = [
    path('', include(router.urls)),
]
