from rest_framework import viewsets, status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample
from users.permissions import IsCustomAuthenticated, RolePermission
from .models import Product, UniqueProduct
from product.serializers import ProductSerializer, UniqueProductSerializer, StockAmountSerializer
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError

from .services import StockService


class ProductViewSet(viewsets.ModelViewSet):
    """ CRUD для карточек товаров."""
    queryset = Product.objects.select_related("shop")
    serializer_class = ProductSerializer
    permission_classes = [IsCustomAuthenticated, RolePermission]
    business_element = "Product"

    @extend_schema(
        summary="Создать товар",
        description=(
            "Создает карточку товара в магазине текущего продавца. "
            "Пользователь может создавать товары только в принадлежащих ему магазинах."
        ),
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


class UniqueProductViewSet(viewsets.ModelViewSet):
    """ CRUD для вариантов товаров.
    Создавать, изменять и удалять варианты может
    только продавец, которому принадлежит магазин товара. """

    queryset = UniqueProduct.objects.select_related(
        "product",
        "product__shop",
    )

    serializer_class = UniqueProductSerializer

    permission_classes = [
        IsCustomAuthenticated,
        RolePermission,
    ]

    business_element = "UniqueProduct"

    @extend_schema(
        summary="Создать вариант товара",
        description=(
            "Создает конкретный вариант товара в магазине продавца. "
            "Вариант может отличаться цветом, размером, артикулом, "
            "ценой и физическими характеристиками. "
            "Вариант можно создать только для товара, принадлежащего "
            "магазину текущего продавца."),
        request=UniqueProductSerializer,
        responses={201: UniqueProductSerializer,
                   400: OpenApiExample(
                       "Bad Request",
                       value={
                           "product": [
                                "Вы можете добавлять варианты только в свои товары."
                           ]
                       },
                       response_only=True,
                   ),
                   401: OpenApiExample(
                       "Unauthorized",
                       value={
                           "detail": "User not authenticated"},
                       response_only=True,
                   ),
                  403: OpenApiExample(
                      "Forbidden",
                      value={
                          "detail": (
                             "You do not have permission " "to create UniqueProduct"
                          )
                      },
                     response_only=True, ), }, )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        summary="Получить список вариантов товаров",
        description=(
            "Возвращает список вариантов товаров. "
            "Продавец получает доступ только к вариантам товаров "
            "своих магазинов в соответствии с правилами доступа."
        ),
        responses={200: UniqueProductSerializer(many=True),
                   401: OpenApiExample("Unauthorized",
                            value={"detail": "User not authenticated"},
                            response_only=True, ),
                   403: OpenApiExample("Forbidden",
                            value={
                           "detail": ("You do not have permission " "to read UniqueProduct")},
                            response_only=True,
                                       ),
                   },
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Получить вариант товара",
        description="Возвращает информацию о конкретном варианте товара.",
        responses={200: UniqueProductSerializer,
                   401: OpenApiExample(
                       "Unauthorized",
                       value={"detail": "User not authenticated"},
                       response_only=True, ),
                   403: OpenApiExample(
                       "Forbidden",
                       value={
                           "detail": ("You do not have permission " "to read UniqueProduct")},
                       response_only=True,
                   ),
                   404: OpenApiExample(
                       "Not Found",
                       value={"detail": "Not found."},
                       response_only=True,
                   ),
                   },
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Изменить вариант товара",
        description=(
            "Полностью изменяет данные варианта товара. "
            "Поле stock недоступно для прямого изменения. "
            "Для изменения остатка необходимо использовать отдельные "
            "эндпоинты пополнения или списания товара."),
                   request=UniqueProductSerializer,
                   responses={200: UniqueProductSerializer,
                              400: OpenApiExample("Bad Request",
                                                  value={"product": [
                                                                   "Вы можете добавлять варианты только в свои товары."]},
                                                  response_only=True, ),
                              401: OpenApiExample("Unauthorized",
                                                  value={
                                                                   "detail": "User not authenticated"},
                                                  response_only=True, ),
                              403: OpenApiExample(
                                  "Forbidden", value={"detail": (
                                                               "You do not have permission " "to update UniqueProduct")},
                                                    response_only=True, ),
                              404: OpenApiExample(
                                  "Not Found", value={"detail": "Not found."},
                                                     response_only=True, ),
                              },
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Частично изменить вариант товара",
        description=(
              "Частично изменяет данные варианта товара. "
              "Поле stock недоступно для прямого изменения."),
                   request=UniqueProductSerializer,
                   responses={
                       200: UniqueProductSerializer,
                       400: OpenApiExample("Bad Request",
                                        value={"detail": "Invalid data"},
                                        response_only=True, ),
                       401: OpenApiExample("Unauthorized",
                                        value={"detail": "User not authenticated"},
                                        response_only=True, ),
                       403: OpenApiExample("Forbidden",
                                           value={"detail": ("You do not have permission " "to update UniqueProduct")},
                                           response_only=True, ),
                       404: OpenApiExample("Not Found",
                                           value={"detail": "Not found."},
                                           response_only=True,
                                           ),
                   },
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Удалить вариант товара",
        description="Удаляет конкретный вариант товара.",
                   responses={
                       204: None,
                       401: OpenApiExample("Unauthorized",
                                           value={"detail": "User not authenticated"},
                                           response_only=True, ),
                       403: OpenApiExample("Forbidden",
                                           value={"detail": ("You do not have permission " "to delete UniqueProduct")},
                                           response_only=True, ),
                       404: OpenApiExample("Not Found",
                                           value={"detail": "Not found."},
                                           response_only=True,
                                           ),
                   },
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Пополнить остаток товара",
        description=(
             "Увеличивает остаток конкретного варианта товара "
             "на складе продавца. "
             "Используется при поступлении новой партии товара "
             "на склад. "
             "Количество должно быть положительным целым числом."),
                   request=StockAmountSerializer,
                   responses={200: OpenApiExample("Success", value={"id": 1, "stock": 15, }, response_only=True, ),
                              400: OpenApiExample("Bad Request",
                                                  value={"amount": ["Количество должно быть больше нуля."]},
                                                  response_only=True, ),
                              401: OpenApiExample("Unauthorized", value={"detail": "User not authenticated"},
                                                  response_only=True, ),
                              403: OpenApiExample("Forbidden",
                                                  value={
                           "detail": ("You do not have permission " "to update UniqueProduct")},
                                                  response_only=True, ),
                              404: OpenApiExample("Not Found",
                                                  value={"detail": "Not found."},
                                                  response_only=True,
                                                  ),
                              },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="stock/increase",
    )
    def increase_stock(self, request, pk=None):
        """ Пополнение остатка товара на складе продавца. """

        unique_product = self.get_object()

        amount = request.data.get("amount")

        if amount is None:
            raise ValidationError(
                {"amount": "Обязательное поле."}
            )

        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValidationError(
                {"amount": "Количество должно быть целым числом."}
            )

        try:
            StockService.increase(
                unique_product=unique_product,
                amount=amount,
            )
        except ValueError as exc:
            raise ValidationError(
                {"amount": str(exc)}
            )

        unique_product.refresh_from_db()

        return Response(
            {
                "id": unique_product.id,
                "stock": unique_product.stock,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Списать товар со склада",
        description=(
            "Уменьшает остаток конкретного варианта товара "
            "на складе продавца. "
            "Используется для списания товара по причине брака, "
            "порчи, утилизации или другой потери товара. "
            "Количество должно быть положительным целым числом " "и не может превышать текущий остаток."),
                   request=StockAmountSerializer,
                   responses={200: OpenApiExample("Success",
                                                  value={"id": 1, "stock": 8, },
                                                  response_only=True, ),
                              400: OpenApiExample("Bad Request",
                                                  value={"amount": ["Недостаточно товара на складе."]},
                                                  response_only=True, ),
                              401: OpenApiExample("Unauthorized",
                                                  value={"detail": "User not authenticated"},
                                                  response_only=True, ),
                              403: OpenApiExample("Forbidden",
                                                  value={
                           "detail": ("You do not have permission " "to update UniqueProduct")},
                                                  response_only=True, ),
                              404: OpenApiExample("Not Found",
                                                  value={"detail": "Not found."},
                                                  response_only=True,
                                                  ),
                              },
    )
    @action(
        detail=True,
        methods=["post"],
        url_path="stock/decrease",
    )
    def decrease_stock(self, request, pk=None):
        """ Списание товара со склада продавца
        по причине брака, порчи, утилизации и т. п. """

        unique_product = self.get_object()

        amount = request.data.get("amount")

        if amount is None:
            raise ValidationError(
                {"amount": "Обязательное поле."}
            )

        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValidationError(
                {"amount": "Количество должно быть целым числом."}
            )

        try:
            StockService.decrease(
                unique_product=unique_product,
                amount=amount,
            )
        except ValueError as exc:
            raise ValidationError(
                {"amount": str(exc)}
            )

        unique_product.refresh_from_db()

        return Response(
            {
                "id": unique_product.id,
                "stock": unique_product.stock,
            },
            status=status.HTTP_200_OK,
        )