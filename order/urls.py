from django.urls import path, include
from rest_framework.routers import DefaultRouter
from order.views import OrderViewSet, ReturnRequestCreateView, ReturnRequestUserListView, ReturnRequestUserDetailView

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path(
            "return-requests/",
            ReturnRequestCreateView.as_view(),
            name="return-request-create",
        ),
    path(
            "return-requests/my/",
            ReturnRequestUserListView.as_view(),
            name="return-request-user-list",
        ),
    path(
            "return-requests/my/<int:pk>/",
            ReturnRequestUserDetailView.as_view(),
            name="return-request-user-detail",
        ),

]
