from typing import Literal

from pydantic import BaseModel

Status = Literal["ok", "erro"]


class HealthOut(BaseModel):
    status: Status
    database: Status
    redis: Status
