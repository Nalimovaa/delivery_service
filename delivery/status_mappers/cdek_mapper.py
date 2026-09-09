from delivery.status_mappers.base import BaseDeliveryStatusMapper
from order.enams import OrderDeliveryStatus


class CdekDeliveryStatusMapper(BaseDeliveryStatusMapper):
    """
    Преобразует статусы CDEK в универсальные статусы OrderDelivery.
    """

    STATUS_MAP = {
        "1": OrderDeliveryStatus.CONFIRMED,
        "2": OrderDeliveryStatus.CANCELLED,
        "3": OrderDeliveryStatus.IN_TRANSIT,
        "4": OrderDeliveryStatus.DELIVERED,
        "5": OrderDeliveryStatus.FAILED,
        "6": OrderDeliveryStatus.IN_TRANSIT,
        "7": OrderDeliveryStatus.IN_TRANSIT,
        "8": OrderDeliveryStatus.IN_TRANSIT,
        "9": OrderDeliveryStatus.IN_TRANSIT,
        "10": OrderDeliveryStatus.IN_TRANSIT,
        "11": OrderDeliveryStatus.IN_TRANSIT,
        "12": OrderDeliveryStatus.IN_TRANSIT,
        "13": OrderDeliveryStatus.IN_TRANSIT,
        "16": OrderDeliveryStatus.IN_TRANSIT,
        "17": OrderDeliveryStatus.IN_TRANSIT,
        "18": OrderDeliveryStatus.IN_TRANSIT,
        "19": OrderDeliveryStatus.IN_TRANSIT,
        "20": OrderDeliveryStatus.IN_TRANSIT,
        "21": OrderDeliveryStatus.IN_TRANSIT,
        "22": OrderDeliveryStatus.IN_TRANSIT,
        "27": OrderDeliveryStatus.IN_TRANSIT,
        "28": OrderDeliveryStatus.IN_TRANSIT,
    }

    STATUS_1000_MAP = {
        "ENTERED_TO_TRANSIT_WAREHOUSE": OrderDeliveryStatus.IN_TRANSIT,
        "ENTERED_TO_RECIPIENT_CITY_WAREHOUSE": OrderDeliveryStatus.IN_TRANSIT,
        "ENTERED_TO_PICK_UP_POINT": OrderDeliveryStatus.IN_TRANSIT,

        "IN_CUSTOMS_INTERNATIONAL": OrderDeliveryStatus.IN_TRANSIT,
        "SHIPPED_TO_DESTINATION": OrderDeliveryStatus.IN_TRANSIT,
        "PASSED_TO_TRANSIT_CARRIER": OrderDeliveryStatus.IN_TRANSIT,
        "IN_CUSTOMS_LOCAL": OrderDeliveryStatus.IN_TRANSIT,
        "CUSTOMS_COMPLETE": OrderDeliveryStatus.IN_TRANSIT,

        "POSTOMAT_POSTED": OrderDeliveryStatus.IN_TRANSIT,
        "POSTOMAT_SEIZED": OrderDeliveryStatus.FAILED,
        "POSTOMAT_RECEIVED": OrderDeliveryStatus.DELIVERED,
    }

    @classmethod
    def map(
        cls,
        *,
        status_code: str,
        status_name: str | None = None,
    ) -> OrderDeliveryStatus:

        if status_code == "1000":
            try:
                return cls.STATUS_1000_MAP[status_name]
            except KeyError:
                raise ValueError(
                    f"Неизвестный статус CDEK "
                    f"с кодом 1000: {status_name}"
                )

        try:
            return cls.STATUS_MAP[status_code]
        except KeyError:
            raise ValueError(
                f"Неизвестный статус CDEK: "
                f"code={status_code}, name={status_name}"
            )