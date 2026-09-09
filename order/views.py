from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.exceptions import NotFound
from delivery.facade import DeliveryFacade
from order.models import Order
from order.serializers import CreateOrderRequestSerializer, CreateOrderResponseSerializer, OrderStatusSerializer
from users.permissions import IsCustomAuthenticated, RolePermission
from rest_framework import status, viewsets



class OrderViewSet(viewsets.ViewSet):
    """
    Создание заказа пользователя.

    Заказ создается на основе текущей корзины пользователя.
    Для каждого магазина передается выбранный тариф доставки
    и данные для оформления доставки.

    Регистрация отправления в транспортной компании может
    выполняться асинхронно. Поэтому успешный ответ endpoint
    означает принятие заказа системой, а не окончательное
    подтверждение регистрации отправления.
    """

    permission_classes = [IsCustomAuthenticated, RolePermission]

    business_element = "Order"

    @extend_schema(
        summary="Создание заказа",
        description=(
            "Создает заказ на основе текущей корзины пользователя.\n\n"

            "Для каждого магазина необходимо передать:\n"
            "1. выбранный тариф доставки;\n"
            "2. данные доставки.\n\n"

            "Во время создания заказа:\n"
            "- проверяется наличие товаров в корзине;\n"
            "- блокируются остатки товаров;\n"
            "- повторно рассчитывается доставка;\n"
            "- создается Order;\n"
            "- создаются OrderDelivery и OrderProduct;\n"
            "- создается отправление в соответствующей транспортной компании.\n\n"

            "После передачи отправления в CDEK его окончательная "
            "регистрация выполняется асинхронно. Номер отслеживания "
            "появится после подтверждения регистрации отправления."
        ),
        request=CreateOrderRequestSerializer,
        responses={
            202: CreateOrderResponseSerializer,

            400: OpenApiExample(
                "Validation error",
                value={
                    "detail": "Корзина пуста.",
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
        """Создает заказ пользователя на основе текущей корзины и переданных данных доставки."""
        serializer = CreateOrderRequestSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        selected_tariffs = {
            int(shop_id): tariff_code
            for shop_id, tariff_code
            in serializer.validated_data["selected_tariffs"].items()
        }

        delivery_data = {
            int(shop_id): data
            for shop_id, data
            in serializer.validated_data["delivery_data"].items()
        }

        order = DeliveryFacade().create_order(
            user=request.user,
            selected_tariffs=selected_tariffs,
            delivery_data=delivery_data,
        )

        return Response(
            {
                "order_id": order.id,
                "status": order.get_status_display(),
                "message": (
                    "Заказ принят. "
                    "Регистрация отправления в транспортной "
                    "компании выполняется. "
                    "Номер отслеживания появится после "
                    "подтверждения регистрации."
                ),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        summary="Получение заказа",
        description=(
            "Возвращает заказ пользователя с полной информацией "
            "об отправлениях.\n\n"
            "В ответе содержатся:\n"
            "- общая информация о заказе;\n"
            "- текущий статус заказа;\n"
            "- отправления по магазинам;\n"
            "- текущий статус каждого отправления;\n"
            "- товары в каждом отправлении;\n"
            "- данные CDEK для отправления;\n"
            "- история статусов CDEK."),
                   responses={
                       200: OrderStatusSerializer,
                       401: OpenApiExample(
                           "Unauthorized", value={"detail": "User not authenticated",
                            },
                       ),
                       403: OpenApiExample(
                           "Forbidden",
                           value={"detail": "You do not have permission", },
                       ),
                       404: OpenApiExample(
                           "Not found",
                           value={"detail": "Заказ не найден.", },
                       ),
                   },
    )
    def retrieve(self, request, pk=None):
        """
        Возвращает заказ пользователя со статусами отправлений.
        """

        order = (
            Order.objects
            .filter(
                id=pk,
                owner=request.user,
            )
            .prefetch_related(
                "deliveries",
                "deliveries__items",
                "deliveries__cdek",
                "deliveries__cdek__status_history",
            )
            .first()
        )

        if order is None:
            raise NotFound("Заказ не найден.")

        serializer = OrderStatusSerializer(order)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

