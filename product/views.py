from rest_framework import viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from users.permissions import IsCustomAuthenticated, RolePermission
from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    """ CRUD for products.
    Checking permissions via RolePermission """
    queryset = Product.objects.select_related("shop")
    serializer_class = ProductSerializer
    permission_classes = [IsCustomAuthenticated, RolePermission]
    business_element = "Product"

    @extend_schema(
        summary="Создать продукт",
        description="Создает новый продукт для выбранного магазина",
        request=ProductSerializer,
        responses={
            201: ProductSerializer,
            400: OpenApiExample("Bad Request", value={"detail": "Invalid data"}),
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to create product"}),
        }
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()

