from rest_framework import viewsets
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from delivery.factories.delivery import DeliveryFactory
from seller.models import Shop, SellerRequest
from seller.serializers import ShopSerializer, ShopDeliverySettingSerializer, ShopDeliverySettingReadSerializer, \
    SellerRequestSerializer, SellerRequestRejectSerializer
from users.models import Role, UserRole
from users.permissions import IsCustomAuthenticated, RolePermission
from seller.services import ShopDeliverySettingService, SellerService, SellerRequestService
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError


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
        user = self.request.user

        with transaction.atomic():
            shop = serializer.save(owner=user)

            DeliveryFactory.initialize(shop)

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
        """Partial store update by ID."""

        shop = self.get_object()
        old_carrier = shop.carrier

        serializer = self.get_serializer(
            shop,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        shop = serializer.save()

        if old_carrier != shop.carrier:
            DeliveryFactory.cleanup(shop, old_carrier)
            DeliveryFactory.initialize(shop)

        return Response(serializer.data)

    @extend_schema(
        summary="Удалить магазин",
        description="Удаляет магазин по ID",
        responses={
            204: OpenApiExample("Deleted", value={"detail": "Shop deleted"}),
            401: OpenApiExample(
                "Unauthorized",
                value={"detail": "User not authenticated"}
            ),
            403: OpenApiExample(
                "Forbidden",
                value={"detail": "You do not have permission to delete this shop"}
            ),
            404: OpenApiExample(
                "Not Found",
                value={"detail": "Shop not found"}
            ),
        }
    )
    def destroy(self, request, *args, **kwargs):
        """Delete store by ID."""

        shop = self.get_object()
        owner = shop.owner

        with transaction.atomic():
            DeliveryFactory.cleanup(shop)

            shop.delete()

            SellerService.remove_role_if_no_shops(owner)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ShopDeliverySettingViewSet(viewsets.ViewSet):
    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "ShopDeliverySetting"

    @extend_schema(
        summary="Получить выбранные тарифы ЛК магазина",
        responses={
            200: ShopDeliverySettingReadSerializer(many=True),
        },
    )
    def list(self, request, shop_pk=None):
        shop = self.get_user_shop(request, shop_pk)

        settings = (
            ShopDeliverySettingService()
            .get_shop_tariffs(shop)
        )

        serializer = ShopDeliverySettingReadSerializer(
            settings,
            many=True,
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Сохранить выбранные тарифы в ЛК магазина",
        request=ShopDeliverySettingSerializer,
        responses={204: None},
    )
    def create(self, request, shop_pk=None):
        shop = self.get_user_shop(request, shop_pk)

        serializer = ShopDeliverySettingSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        ShopDeliverySettingService().save(
            shop=shop,
            tariff_codes=serializer.validated_data["tariffs"],
        )

        return Response(status=204)

    @extend_schema(
        summary="Очистить выбранные тарифы ЛК магазина",
        responses={204: None},
    )
    def destroy(self, request, shop_pk=None):
        shop = self.get_user_shop(request, shop_pk)

        ShopDeliverySettingService().clear(shop)

        return Response(status=204)

    def get_user_shop(self, request, shop_pk):
        return get_object_or_404(
            Shop,
            pk=shop_pk,
            owner=request.user,
        )




class SellerRequestViewSet(viewsets.ModelViewSet):
    """Заявки пользователей на получение роли Seller."""

    queryset = SellerRequest.objects.select_related("user")

    serializer_class = SellerRequestSerializer

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "SellerRequest"

    @extend_schema(
        summary="Подать заявку на получение роли Seller",
        description=(
            "Создает заявку текущего пользователя на получение роли Seller. "
            "Если пользователь уже является продавцом или его заявка "
            "уже находится на рассмотрении, создание новой заявки запрещено. "
            "После отклонения заявки пользователь может подать новую."
        ),
        request=None,
        responses={
            201: SellerRequestSerializer,
            400: OpenApiExample(
                "Bad Request",
                value={
                    "detail": "Заявка уже находится на рассмотрении."
                },
            ),
            401: OpenApiExample(
                "Unauthorized",
                value={
                    "detail": "Пользователь не авторизован."
                },
            ),
            403: OpenApiExample(
                "Forbidden",
                value={
                    "detail": "Нет прав на создание заявки."
                },
            ),
        },
    )
    def create(self, request, *args, **kwargs):
        """Создание заявки текущим пользователем."""

        try:
            seller_request = SellerRequestService.create(
                request.user,
            )
        except ValueError as exc:
            raise ValidationError(
                {"detail": str(exc)}
            )

        serializer = self.get_serializer(
            seller_request,
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Одобрить заявку",
        description=(
            "Одобряет заявку пользователя на получение роли Seller. "
            "После одобрения пользователю автоматически назначается роль Seller."
        ),
        request=None,
        responses={
            200: OpenApiExample(
                "Success",
                value={
                    "detail": (
                        "Заявка одобрена. "
                        "Пользователь получил роль Seller."
                    )
                },
            ),
            400: OpenApiExample(
                "Bad Request",
                value={
                    "detail": (
                        "Можно одобрить только заявку, "
                        "находящуюся на рассмотрении."
                    )
                },
            ),
            401: OpenApiExample(
                "Unauthorized",
                value={
                    "detail": "Пользователь не авторизован."
                },
            ),
            403: OpenApiExample(
                "Forbidden",
                value={
                    "detail": "Недостаточно прав."
                },
            ),
            404: OpenApiExample(
                "Not Found",
                value={
                    "detail": "Заявка не найдена."
                },
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="approve",
    )
    def approve(self, request, pk=None):
        """Одобрение заявки администратором."""

        seller_request = self.get_object()

        try:
            SellerRequestService.approve(
                seller_request,
            )
        except ValueError as exc:
            raise ValidationError(
                {"detail": str(exc)}
            )

        return Response(
            {
                "detail": (
                    "Заявка одобрена. "
                    "Пользователь получил роль Seller."
                )
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Отклонить заявку",
        description=(
            "Отклоняет заявку пользователя на получение роли Seller. "
            "При отклонении необходимо указать причину. "
            "После отклонения пользователь сможет подать новую заявку."
        ),
        request=SellerRequestRejectSerializer,
        responses={
            200: OpenApiExample(
                "Success",
                value={
                    "detail": "Заявка отклонена."
                },
            ),
            400: OpenApiExample(
                "Bad Request",
                value={
                    "detail": "Необходимо указать причину отказа."
                },
            ),
            401: OpenApiExample(
                "Unauthorized",
                value={
                    "detail": "Пользователь не авторизован."
                },
            ),
            403: OpenApiExample(
                "Forbidden",
                value={
                    "detail": "Недостаточно прав."
                },
            ),
            404: OpenApiExample(
                "Not Found",
                value={
                    "detail": "Заявка не найдена."
                },
            ),
        },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="reject",
    )
    def reject(self, request, pk=None):
        """Отклонение заявки администратором."""

        seller_request = self.get_object()

        serializer = SellerRequestRejectSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        try:
            SellerRequestService.reject(
                seller_request=seller_request,
                reason=serializer.validated_data["reason"],
            )
        except ValueError as exc:
            raise ValidationError(
                {"detail": str(exc)}
            )

        return Response(
            {
                "detail": "Заявка отклонена.",
            },
            status=status.HTTP_200_OK,
        )
