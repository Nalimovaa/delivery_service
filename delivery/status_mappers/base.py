from abc import ABC, abstractmethod


class BaseDeliveryStatusMapper(ABC):
    """
    Базовый mapper статусов транспортной компании
    во внутренний статус отправления.
    """

    @classmethod
    @abstractmethod
    def map(
        cls,
        *,
        status_code: str,
        status_name: str | None = None,
    ):
        raise NotImplementedError