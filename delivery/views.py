from rest_framework import viewsets
from rest_framework.response import Response
from delivery.facade import DeliveryFacade
from django.conf import settings
from delivery.serializers import CDEKTariffSerializer, ShopDeliveryResultSerializer, CalculateDeliveryRequestSerializer, \
    CartDeliveryResultSerializer, CDEKDeliveryPointSerializer, APIWebhookOrderStatusSerializer
from delivery.services.locations import CDEKDeliveryPointService
from delivery.services.order import CdekWebhookService
from delivery.services.tariffs import CDEKTariffService
from drf_spectacular.utils import extend_schema, OpenApiExample
from users.permissions import IsCustomAuthenticated, RolePermission
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied


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


class DeliveryPointsViewSet(viewsets.ViewSet):
    """
    Получение списка пунктов выдачи и приема CDEK.

    Возвращает актуальный список ПВЗ CDEK, полученный из локального
    Redis-кэша или базы данных.

    Список ПВЗ синхронизируется с API CDEK фоновой Celery-задачей.
    """

    permission_classes = [IsCustomAuthenticated, RolePermission]

    # Пользователь имеет read/create/update/delete права на Cart.
    business_element = "Cart"

    @extend_schema(
        summary="Получить список ПВЗ CDEK",
        description=(
            "Возвращает список актуальных пунктов выдачи и приема "
            "CDEK, доступных для выбора при оформлении доставки.\n\n"

            "ПВЗ предварительно синхронизируются с API CDEK "
            "фоновой Celery-задачей и сохраняются в PostgreSQL "
            "и Redis.\n\n"

            "При запросе приложение использует локальные данные, "
            "не выполняя прямой запрос к API CDEK.\n\n"

            "В ответе для каждого ПВЗ возвращаются:\n"
            "- код ПВЗ;\n"
            "- название;\n"
            "- тип ПВЗ;\n"
            "- статус;\n"
            "- страна и регион;\n"
            "- город;\n"
            "- почтовый индекс;\n"
            "- адрес;\n"
            "- координаты;\n"
            "- UUID ПВЗ и города.\n\n"

            "Возвращаются только активные ПВЗ."
        ),
        responses={
            200: CDEKDeliveryPointSerializer(many=True),

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
    def list(self, request):
        """
        Возвращает список актуальных ПВЗ CDEK.
        """

        delivery_points = (
            CDEKDeliveryPointService()
            .get_delivery_points()
        )

        return Response(delivery_points)




class CdekWebhookOrderStatusView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    ALLOWED_IPS = settings.ALLOWED_IPS_CDEK_WEBHOOKS

    @extend_schema(
        summary="Получить webhook CDEK об изменении статуса заказа",
        description=(
            "Принимает уведомление от CDEK об изменении статуса заказа."
        ),
        request=APIWebhookOrderStatusSerializer,
        responses={
            200: None,

            400: OpenApiExample(
                "Bad Request",
                value={
                    "detail": "Invalid webhook data.",
                },
            ),

            403: OpenApiExample(
                "Forbidden",
                value={
                    "detail": "IP address is not allowed.",
                },
            ),

            404: OpenApiExample(
                "Not Found",
                value={
                    "detail": "CDEK delivery not found.",
                },
            ),
        },
    )
    def post(self, request: Request):
        client_ip = self.get_client_ip(request)
        self.validate_ip(client_ip)

        serializer = APIWebhookOrderStatusSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        data = serializer.validated_data
        attributes = data["attributes"]

        CdekWebhookService().process_order_status(
            cdek_uuid=str(data["uuid"]),
            cdek_number=attributes["cdek_number"],
            status_code=attributes["code"],
            status_date_time=attributes["status_date_time"],
            status_name=attributes.get("name", ""),
            city=attributes.get("city"),
        )

        return Response(
            status=status.HTTP_200_OK,
        )

    def get_client_ip(self, request: Request) -> str:
        return request.META.get("REMOTE_ADDR", "")

    def validate_ip(self, client_ip: str) -> None:
        if client_ip not in self.ALLOWED_IPS:
            raise PermissionDenied(
                "IP address is not allowed.",
            )