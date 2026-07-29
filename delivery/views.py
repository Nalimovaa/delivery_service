from rest_framework import viewsets
from rest_framework.response import Response

from delivery.serializers import CDEKTariffSerializer
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