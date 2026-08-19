from rest_framework import viewsets
from rest_framework.response import Response

from delivery.facade import DeliveryFacade
from delivery.schemas.tariffs import ShopDeliveryResultDTO
from delivery.serializers import CDEKTariffSerializer, ShopDeliveryResultSerializer, CalculateDeliveryRequestSerializer, \
    CartDeliveryResultSerializer
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


class DeliveryCalculationViewSet(viewsets.ViewSet):
    """
    Расчет итоговой стоимости доставки товаров текущей корзины
    по выбранным пользователем тарифам для каждого магазина.

    Для каждого магазина в корзине пользователь предварительно
    выбирает тариф доставки. В запрос передается соответствие
    shop_id -> tariff_code.

    Для каждого магазина вызывается соответствующий сервис
    доставки через DeliveryFactory.
    """

    permission_classes = [IsCustomAuthenticated, RolePermission]

    # Пользователь имеет read/create/update/delete права на Cart.
    # POST будет проверяться через create_permission.
    business_element = "Cart"

    @extend_schema(
        summary="Расчет стоимости корзины по выбранным тарифам",
        description=(
            "Выполняет расчет итоговой стоимости товаров и доставки "
            "для всех магазинов текущей корзины.\n\n"

            "Корзина пользователя группируется по магазинам. "
            "Для каждого магазина передается выбранный пользователем "
            "тариф доставки в формате shop_id -> tariff_code.\n\n"

            "Для каждого магазина:\n"
            "1. Проверяется наличие выбранного тарифа в настройках магазина.\n"
            "2. Получаются актуальные товары корзины данного магазина.\n"
            "3. Получается актуальная стоимость товаров магазина.\n"
            "4. Выполняется расчет доставки через соответствующий "
            "сервис транспортной компании.\n"
            "5. Формируется итоговая стоимость группы товаров "
            "(товары + доставка).\n\n"

            "В ответе возвращается отдельный результат по каждому "
            "магазину, а также итоговая стоимость всей корзины."
        ),
        request=CalculateDeliveryRequestSerializer,
        responses={
            200: CartDeliveryResultSerializer,

            400: OpenApiExample(
                "Validation error",
                value={
                    "detail": "Для магазина не выбран тариф доставки",
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
        Рассчитывает итоговую стоимость корзины
        по выбранным пользователем тарифам.
        """

        serializer = CalculateDeliveryRequestSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        selected_tariffs = serializer.validated_data["selected_tariffs"]

        result = DeliveryFacade().calculate_delivery(
            user=request.user,
            selected_tariffs=selected_tariffs,
        )

        return Response(
            result.model_dump(mode="json")
        )