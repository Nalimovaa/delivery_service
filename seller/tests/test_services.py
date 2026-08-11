""" docker exec -it delivery_service-web-1 python manage.py test seller.tests.test_services """

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from delivery.enums import DeliveryType
from delivery.models import CDEKTariff
from seller.models import Shop, ShopDeliverySetting, SellerRequestStatus, SellerRequest
from seller.services import ShopDeliverySettingService, SellerService, SellerRequestService
from users.models import User, Role, UserRole


class TestShopDeliverySettingService(TestCase):
    """
    Тесты сервиса ShopDeliverySettingService.

    Проверяется:
    - сохранение выбранных тарифов магазина;
    - проверка доступности тарифов перед сохранением;
    - получение выбранных тарифов магазина;
    - удаление сохраненных настроек магазина.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.shop = Shop.objects.create(
            owner=self.user,
            name="Shop",
            carrier=DeliveryType.CDEK,
        )

        self.tariff = CDEKTariff.objects.create(
            tariff_code=499,
            tariff_name="Business",
            delivery_mode=1,
            delivery_mode_name="дверь-дверь",
            weight_min=Decimal("0.000"),
            weight_max=Decimal("1000.000"),
            length_max=1000,
            width_max=1000,
            height_max=1000,
            is_active=True,
        )

        self.service = ShopDeliverySettingService()

    @patch.object(
        ShopDeliverySettingService,
        "get_available_tariff_codes",
    )
    def test_save_tariffs(self, mocked_codes):
        """Проверяет успешное сохранение выбранных тарифов магазина."""

        mocked_codes.return_value = {499}

        self.service.save(
            shop=self.shop,
            tariff_codes=[499],
        )

        self.assertEqual(
            ShopDeliverySetting.objects.count(),
            1,
        )

    @patch.object(
        ShopDeliverySettingService,
        "get_available_tariff_codes",
    )
    def test_invalid_tariff(self, mocked_codes):
        """Проверяет, что при выборе недоступного тарифа возникает ValueError."""

        mocked_codes.return_value = {499}

        with self.assertRaises(ValueError):
            self.service.save(
                shop=self.shop,
                tariff_codes=[111],
            )

    def test_get_shop_tariffs(self):
        """Проверяет получение списка тарифов, выбранных магазином."""

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        tariffs = self.service.get_shop_tariffs(
            self.shop,
        )

        self.assertEqual(
            tariffs.count(),
            1,
        )

    def test_clear(self):
        """Проверяет удаление всех сохраненных тарифов магазина."""

        ShopDeliverySetting.objects.create(
            shop=self.shop,
            tariff=self.tariff,
        )

        self.service.clear(
            self.shop,
        )

        self.assertEqual(
            ShopDeliverySetting.objects.count(),
            0,
        )


class TestSellerService(TestCase):

    def setUp(self):
        self.user = User.objects.create(
            email="seller@test.com",
        )

        self.role = Role.objects.create(
            name="Seller",
        )

    def test_assign_role(self):
        SellerService.assign_role(
            self.user,
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )

    def test_remove_role_if_no_shops(self):
        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        SellerService.remove_role_if_no_shops(
            self.user,
        )

        self.assertFalse(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )

    def test_keep_role_if_user_has_shop(self):
        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        Shop.objects.create(
            owner=self.user,
            name="Test shop",
            carrier=DeliveryType.CDEK,
        )

        SellerService.remove_role_if_no_shops(
            self.user,
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )


class TestSellerRequestService(TestCase):
    """
    Тесты SellerRequestService.

    Проверяется:
    - создание заявки;
    - запрет повторной заявки, если текущая находится на рассмотрении;
    - возможность повторной подачи после отклонения;
    - одобрение заявки;
    - назначение роли Seller после одобрения;
    - отклонение заявки с причиной;
    - запрет одобрения/отклонения уже обработанной заявки.
    """

    def setUp(self):
        self.user = User.objects.create(
            email="user@test.com",
        )

        self.role = Role.objects.create(
            name="Seller",
        )

    def test_create_request(self):
        """Пользователь может создать заявку на получение роли Seller."""

        seller_request = SellerRequestService.create(
            self.user,
        )

        self.assertEqual(
            seller_request.user,
            self.user,
        )

        self.assertEqual(
            seller_request.status,
            SellerRequestStatus.PENDING,
        )

        self.assertIsNone(
            seller_request.rejection_reason,
        )

    def test_create_request_when_pending_exists(self):
        """Нельзя создать вторую заявку, пока первая находится на рассмотрении."""

        SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Заявка уже находится на рассмотрении.",
        ):
            SellerRequestService.create(
                self.user,
            )

    def test_create_request_when_user_already_seller(self):
        """Продавец не может повторно подавать заявку."""

        UserRole.objects.create(
            user=self.user,
            role=self.role,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Пользователь уже является продавцом.",
        ):
            SellerRequestService.create(
                self.user,
            )

    def test_create_request_after_rejected(self):
        """После отклонения пользователь может подать новую заявку."""

        SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.REJECTED,
            rejection_reason="Недостаточно данных.",
        )

        seller_request = SellerRequestService.create(
            self.user,
        )

        self.assertEqual(
            seller_request.status,
            SellerRequestStatus.PENDING,
        )

        self.assertIsNone(
            seller_request.rejection_reason,
        )

        self.assertEqual(
            SellerRequest.objects.filter(
                user=self.user,
            ).count(),
            2,
        )

    def test_approve_request(self):
        """Одобрение заявки назначает пользователю роль Seller."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        result = SellerRequestService.approve(
            seller_request,
        )

        seller_request.refresh_from_db()

        self.assertEqual(
            result.id,
            seller_request.id,
        )

        self.assertEqual(
            seller_request.status,
            SellerRequestStatus.APPROVED,
        )

        self.assertIsNone(
            seller_request.rejection_reason,
        )

        self.assertTrue(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).exists()
        )

    def test_approve_request_is_idempotent_for_role(self):
        """
        Проверяет, что роль не дублируется.

        Повторное одобрение самой заявки запрещено,
        но UserRole.objects.get_or_create() не создаёт дубликат роли.
        """

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        SellerRequestService.approve(
            seller_request,
        )

        self.assertEqual(
            UserRole.objects.filter(
                user=self.user,
                role=self.role,
            ).count(),
            1,
        )

    def test_approve_rejected_request(self):
        """Нельзя одобрить уже отклоненную заявку."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.REJECTED,
            rejection_reason="Причина отказа.",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Можно одобрить только заявку, находящуюся на рассмотрении.",
        ):
            SellerRequestService.approve(
                seller_request,
            )

        seller_request.refresh_from_db()

        self.assertEqual(
            seller_request.status,
            SellerRequestStatus.REJECTED,
        )

    def test_reject_request(self):
        """Отклонение заявки сохраняет статус и причину."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        result = SellerRequestService.reject(
            seller_request=seller_request,
            reason="Необходимо предоставить дополнительные документы.",
        )

        seller_request.refresh_from_db()

        self.assertEqual(
            result.id,
            seller_request.id,
        )

        self.assertEqual(
            seller_request.status,
            SellerRequestStatus.REJECTED,
        )

        self.assertEqual(
            seller_request.rejection_reason,
            "Необходимо предоставить дополнительные документы.",
        )

    def test_reject_request_strips_reason(self):
        """Причина отказа очищается от пробелов по краям."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        SellerRequestService.reject(
            seller_request=seller_request,
            reason="   Недостаточно данных.   ",
        )

        seller_request.refresh_from_db()

        self.assertEqual(
            seller_request.rejection_reason,
            "Недостаточно данных.",
        )

    def test_reject_request_without_reason(self):
        """Нельзя отклонить заявку без причины."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Необходимо указать причину отказа.",
        ):
            SellerRequestService.reject(
                seller_request=seller_request,
                reason="",
            )

    def test_reject_request_with_whitespace_reason(self):
        """Нельзя использовать строку из одних пробелов как причину."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.PENDING,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Необходимо указать причину отказа.",
        ):
            SellerRequestService.reject(
                seller_request=seller_request,
                reason="   ",
            )

    def test_reject_approved_request(self):
        """Нельзя отклонить уже одобренную заявку."""

        seller_request = SellerRequest.objects.create(
            user=self.user,
            status=SellerRequestStatus.APPROVED,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Можно отклонить только заявку, находящуюся на рассмотрении.",
        ):
            SellerRequestService.reject(
                seller_request=seller_request,
                reason="Причина отказа.",
            )