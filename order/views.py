from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.exceptions import NotFound
from delivery.facade import DeliveryFacade
from delivery.serializers import CDEKClientReturnCreateSerializer, CdekReturnSerializer
from delivery.services.order import CDEKOrderService
from order.models import Order, ReturnRequest
from order.serializers import CreateOrderRequestSerializer, CreateOrderResponseSerializer, OrderStatusSerializer, \
    ReturnRequestSerializer, ReturnRequestCreateSerializer
from order.services import ReturnRequestService
from users.permissions import IsCustomAuthenticated, RolePermission
from rest_framework import status, viewsets
from drf_spectacular.utils import (
    extend_schema,
    OpenApiExample,
    OpenApiResponse,
)
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404



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

    {
            "selected_tariffs": {
                "1": 139,
                "4": 137
            },
            "delivery_data": {
                "1": {
                    "address_to": "ул. Кооперативная, д. 102А",
                    "postal_code_to": "446370"
                },
                "4": {
                    "address_to": "ул. Кооперативная, д. 102А",
                    "postal_code_to": "446370"
                }
            }
        }

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


class ReturnRequestCreateView(APIView):
    """
    Создание покупателем заявки на возврат доставленного заказа.

    Заявка может быть создана только для заказа,
    принадлежащего текущему пользователю, и только после его доставки.
    """

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "ReturnRequest"

    @extend_schema(
        summary="Создание заявки на возврат заказа",
        description=(
            "Создает заявку покупателя на возврат доставленного заказа.\n\n"

            "Для создания заявки необходимо, чтобы:\n"
            "1. доставка заказа существовала;\n"
            "2. заказ принадлежал текущему пользователю;\n"
            "3. доставка имела статус «Доставлена».\n\n"

            "После успешного создания заявка получает статус "
            "`REQUESTED` и передается магазину на рассмотрение."
        ),
        request=ReturnRequestCreateSerializer,
        responses={
            201: ReturnRequestSerializer,
            400: OpenApiResponse(
                description="Ошибка валидации или условия возврата не выполнены.",
            ),
            401: OpenApiResponse(
                description="Пользователь не авторизован.",
            ),
            403: OpenApiResponse(
                description="Недостаточно прав.",
            ),
        },
    )
    def post(self, request):
        serializer = ReturnRequestCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        service = ReturnRequestService()

        return_request = service.create(
            user=request.user,
            order_delivery=serializer.validated_data["order_delivery"],
            reason=serializer.validated_data["reason"],
        )

        response_serializer = ReturnRequestSerializer(
            return_request,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


class ReturnRequestUserListView(APIView):
    """
    Просмотр покупателем списка собственных заявок
    на возврат заказов.
    """

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "ReturnRequest"

    @extend_schema(
        summary="Список заявок покупателя на возврат",
        description=(
            "Возвращает список заявок на возврат, "
            "созданных текущим пользователем."
        ),
        responses={
            200: ReturnRequestSerializer(many=True),
            401: OpenApiResponse(
                description="Пользователь не авторизован.",
            ),
            403: OpenApiResponse(
                description="Недостаточно прав.",
            ),
        },
    )
    def get(self, request):
        return_requests = (
            ReturnRequest.objects
            .filter(owner=request.user)
            .select_related(
                "owner",
                "order_delivery",
                "order_delivery__shop",
                "order_delivery__shop__owner",
            )
            .order_by("-created_at")
        )

        serializer = ReturnRequestSerializer(
            return_requests,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )



class ReturnRequestUserDetailView(APIView):
    """
    Просмотр покупателем конкретной собственной заявки
    на возврат заказа.
    """

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "ReturnRequest"

    @extend_schema(
        summary="Просмотр заявки покупателем",
        description=(
            "Возвращает информацию о конкретной заявке "
            "на возврат заказа.\n\n"
            "Покупатель может просматривать только заявки, "
            "созданные им самим."
        ),
        responses={
            200: ReturnRequestSerializer,
            401: OpenApiResponse(
                description="Пользователь не авторизован.",
            ),
            403: OpenApiResponse(
                description="Недостаточно прав.",
            ),
            404: OpenApiResponse(
                description="Заявка не найдена.",
            ),
        },
    )
    def get(self, request, pk):
        return_request = get_object_or_404(
            ReturnRequest.objects.select_related(
                "owner",
                "order_delivery",
                "order_delivery__shop",
                "order_delivery__shop__owner",
            ),
            pk=pk,
        )

        self.check_object_permissions(
            request,
            return_request,
        )

        serializer = ReturnRequestSerializer(
            return_request,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )



class CDEKClientReturnCreateView(APIView):
    """
    Создание клиентского возврата
    в системе CDEK для одобренной заявки.
    """

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "ReturnRequest"

    @extend_schema(
        summary="Создание возврата в CDEK",
        description=(
            "Регистрирует клиентский возврат "
            "в системе CDEK для одобренной заявки."
        ),
        request=CDEKClientReturnCreateSerializer,
        responses={
            201: CdekReturnSerializer,
            400: OpenApiResponse(
                description=(
                    "Ошибка валидации или бизнес-ошибка CDEK."
                ),
            ),
            401: OpenApiResponse(
                description="Пользователь не авторизован.",
            ),
            403: OpenApiResponse(
                description="Недостаточно прав.",
            ),
            404: OpenApiResponse(
                description="Заявка на возврат не найдена.",
            ),
        },
    )
    def post(
        self,
        request,
        pk,
    ):
        return_request = get_object_or_404(
            ReturnRequest.objects.select_related(
                "order_delivery",
                "order_delivery__shop",
                "order_delivery__shop__owner",
            ),
            pk=pk,
        )

        self.check_object_permissions(
            request,
            return_request,
        )

        serializer = CDEKClientReturnCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(
            raise_exception=True,
        )

        service = CDEKOrderService(
            user=request.user,
        )

        cdek_return = service.create_client_return(
            return_request_id=return_request.id,
            tariff_code=serializer.validated_data[
                "tariff_code"
            ],
        )

        response_serializer = CdekReturnSerializer(
            cdek_return,
        )

        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )