from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delivery.views import CDEKTariffViewSet

router = DefaultRouter()


router.register(
    r'alltariffs',
    CDEKTariffViewSet,
    basename="cdek-tariffs",
)

urlpatterns = [
    path('', include(router.urls)),
]