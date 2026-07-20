"""
Иерархия пользовательских исключений, используемых при взаимодействии
с внешним API служб доставок.
"""
from typing import Optional


class DeliveryError(Exception):
    """Базовое исключение модуля доставки."""
    pass


class CDEKApiError(DeliveryError):
    """
    Отлавливает ошибки на транспортном уровне (HTTP 4xx, 5xx) (API СДЭК вернул HTTP-ошибку).
    Не отлавливает ошибки на уровне бизнес-логики (например, неверные параметры запроса).
    """

    def __init__(
        self,
        status_code: int,
        error: Optional[str] = None,
        error_description: Optional[str] = None,
        code: Optional[str] = None,
        additional_code: Optional[str] = None,
        message: Optional[str] = None,
        warnings: Optional[list[dict]] = None,
        response_data: Optional[dict] = None,
    ):
        self.status_code = status_code

        self.error = error
        self.error_description = error_description

        self.code = code
        self.additional_code = additional_code
        self.message = message

        self.warnings = warnings or []

        # полный ответ СДЭК
        self.response_data = response_data or {}

        super().__init__(self.__str__())

    def __str__(self):

        parts = [f"HTTP {self.status_code}"]

        if self.error:
            parts.append(f"error={self.error}")

        if self.error_description:
            parts.append(
                f"error_description='{self.error_description}'"
            )

        if self.code:
            parts.append(f"code={self.code}")

        if self.additional_code:
            parts.append(
                f"additional_code={self.additional_code}"
            )

        if self.message:
            parts.append(f"message='{self.message}'")

        if self.warnings:
            parts.append(f"warnings={len(self.warnings)}")

        return ", ".join(parts)


class CDEKBusinessError(DeliveryError):
    """
    Отлавливает ошибки на бизнес-уровне.
    Ошибка бизнес-операции СДЭК.
    Например:
    - заказ не создан;
    - тариф недоступен;
    - номер заказа уже существует.
    """

    def __init__(
        self,
        operation: str,
        code: Optional[str] = None,
        message: Optional[str] = None,
        response_data: Optional[dict] = None,
    ):
        self.operation = operation
        self.code = code
        self.message = message
        self.response_data = response_data or {}

        super().__init__(self.__str__())

    def __str__(self):
        return (
            f"CDEK business error "
            f"operation={self.operation}, "
            f"code={self.code}, "
            f"message='{self.message}'"
        )