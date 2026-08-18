from rest_framework import viewsets
from rest_framework.response import Response

from delivery.facade import DeliveryFacade
from delivery.schemas.tariffs import ShopDeliveryResultDTO
from delivery.serializers import CDEKTariffSerializer, ShopDeliveryResultSerializer
from delivery.services.tariffs import CDEKTariffService
from drf_spectacular.utils import extend_schema, OpenApiExample
from users.permissions import IsCustomAuthenticated, RolePermission


class CDEKTariffViewSet(viewsets.ViewSet):
    """
    Просмотр всех актуальных тарифов CDEK,
    доступных по договору продавца.
    """

    permission_classes = [IsCustomAuthenticated, RolePermission]
    business_element = "ShopDeliverySetting"

    @extend_schema(
        summary="Получить список тарифов CDEK",
        description=(
                "Возвращает список актуальных тарифов CDEK, "
                "доступных по договору продавца. "
                "Данные берутся из кэша Redis, который обновляется "
                "ежедневно задачей Celery Beat."
        ),
        responses={
            200: CDEKTariffSerializer(many=True),
            401: OpenApiExample(
                "Unauthorized",
                value={"detail": "User not authenticated"},
            ),
        },
    )

    def list(self, request):
        tariffs = CDEKTariffService().get_cached_tariffs()

        serializer = CDEKTariffSerializer(
            tariffs,
            many=True,
        )

        return Response(serializer.data)


class DeliveryPreCalculationViewSet(viewsets.ViewSet):
    """
    Предварительный расчет стоимости доставки товаров,
    находящихся в корзине текущего пользователя.

    Корзина разбивается по магазинам.
    Для каждого магазина выполняется отдельный расчет
    доступных вариантов доставки.
    """

    permission_classes = [IsCustomAuthenticated, RolePermission]

    # Пользователь имеет read/create/update/delete права на Cart.
    # POST будет проверяться через create_permission.
    business_element = "Cart"

    @extend_schema(
        summary="Предварительный расчет стоимости доставки корзины",
        description=(
                "Выполняет предварительный расчет стоимости доставки "
                "всех товаров текущей корзины.\n\n"

                "Корзина пользователя группируется по магазинам. "
                "Для каждого магазина вызывается соответствующий "
                "сервис доставки через DeliveryFactory.\n\n"

                "Для СДЭК:\n"
                "1. Проверяется наличие города и региона отправления "
                "у магазина.\n"
                "2. Проверяется наличие города и региона доставки "
                "у пользователя.\n"
                "3. Города преобразуются в CDEK location code.\n"
                "4. Товары магазина передаются в CDEKAdapter.\n"
                "5. Получается список доступных тарифов.\n"
                "6. Тарифы фильтруются по настройкам магазина.\n\n"

                "В ответе возвращается отдельный объект для каждого "
                "магазина, содержащий список товаров и доступные "
                "варианты доставки."
        ),
        responses={
            200: ShopDeliveryResultSerializer(many=True),

            400: OpenApiExample(
                "Validation error",
                value={
                    "detail": "У пользователя не указан город доставки",
                },
            ),

            401: OpenApiExample(
                "Unauthorized",
                value={
                    "detail": "User not authenticated",
                },
            ),

            403: OpenApiExample(
                "Forbidden",
                value={
                    "detail": "You do not have permission",
                },
            ),
        },
    )
    def create(self, request):
        """
        Предварительный расчет стоимости доставки корзины пользователя.
        """

        results = DeliveryFacade().pre_calculate_delivery(
            user=request.user,
        )

        return Response(
            [
                result.model_dump(mode="json")
                for result in results
            ]
        )