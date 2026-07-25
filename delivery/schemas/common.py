from pydantic import BaseModel, Field
from typing import Optional
from typing import List


class CDEKError(BaseModel):
    code: str
    message: str


class CDEKWarning(BaseModel):
    code: Optional[str] = None
    message: str


class CDEKErrorResponseSchema(BaseModel):
    errors: List[CDEKError] = Field(default_factory=list)
    warnings: List[CDEKWarning] = Field(default_factory=list)