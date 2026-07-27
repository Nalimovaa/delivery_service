from rest_framework import viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import Shop
from .serializers import ShopSerializer, ShopDeliverySettingSerializer
from users.permissions import IsCustomAuthenticated, RolePermission
from .services import ShopDeliverySettingService


class ShopViewSet(viewsets.ModelViewSet):
    """ CRUD for stores.
    Checking permissions via RolePermission """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsCustomAuthenticated, RolePermission]
    business_element = "Shop"

    @extend_schema(
        summary="Создать магазин",
        description="Создает новый магазин и автоматически привязывает его к текущему пользователю",
        request=ShopSerializer,
        responses={
            201: ShopSerializer,
            400: OpenApiExample("Bad Request", value={"detail": "Invalid data"}),
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to create shop"}),
        }
    )
    def create(self, request, *args, **kwargs):
        """Creating a store"""
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary="Список магазинов",
        description="Возвращает все магазины, доступные пользователю",
        responses={
            200: ShopSerializer,
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to view shops"}),
        }
    )
    def list(self, request, *args, **kwargs):
        """Get a list of stores"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Получить магазин",
        description="Возвращает магазин по ID",
        responses={
            200: ShopSerializer,
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to view this shop"}),
            404: OpenApiExample("Not Found", value={"detail": "Shop not found"}),
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """Get store by ID"""
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Частично обновить магазин",
        description="Частично обновляет магазин",
        request=ShopSerializer,
        responses={
            200: ShopSerializer,
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to update this shop"}),
            404: OpenApiExample("Not Found", value={"detail": "Shop not found"}),
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """ Partial store update by ID """
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить магазин",
        description="Удаляет магазин по ID",
        responses={
            204: OpenApiExample("Deleted", value={"detail": "Shop deleted"}),
            401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"}),
            403: OpenApiExample("Forbidden", value={"detail": "You do not have permission to delete this shop"}),
            404: OpenApiExample("Not Found", value={"detail": "Shop not found"}),
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete store by ID"""
        return super().destroy(request, *args, **kwargs)


class ShopDeliverySettingViewSet(viewsets.ViewSet):

    def list(self, request):
        pass

    def create(self, request):
        serializer = ShopDeliverySettingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ShopDeliverySettingService().save(
            shop=request.user.shop,
            tariff_codes=serializer.validated_data["tariffs"],
        )

        return Response(status=204)

    def delete(self, request):
        pass

