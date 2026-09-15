from pydantic import BaseModel, Field


class CDEKOrderAcceptedEvent(BaseModel):
    event: str = "cdek.order.accepted"
    cdek_delivery_id: int
    cdek_uuid: str


class CDEKOrderReadyEvent(BaseModel):
    event: str = "cdek.order.ready"
    cdek_delivery_id: int
    cdek_uuid: str
    cdek_number: str


class CDEKOrderFailedEvent(BaseModel):
    event: str = "cdek.order.failed"
    cdek_delivery_id: int
    cdek_uuid: str
    errors: list[dict] = Field(default_factory=list)


class CDEKOrderDeleteAcceptedEvent(BaseModel):
    event: str = "cdek.order.delete.accepted"
    cdek_delivery_id: int
    cdek_uuid: str


class CDEKClientReturnAcceptedEvent(BaseModel):
    event: str = "cdek.client-return.accepted"
    cdek_return_id: int
    cdek_uuid: str