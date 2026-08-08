from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["up", "down"]


class StatusResponse(BaseModel):
    service: str
    version: str
    environment: str
    status: Literal["operational"]
