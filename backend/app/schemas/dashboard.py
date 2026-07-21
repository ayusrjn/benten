import uuid
from typing import List
from pydantic import BaseModel, ConfigDict

class DashboardAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    desc: str
    type: str


class DashboardMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    conversationsCount: int
    latencyAvg: int
    deadAirAvg: float
    interruptionsCount: int
    voiceQualityAvg: int
    avgDurationSec: int
    latencyTrend: List[int]
    volumeTrend: List[int]
    activeAlerts: List[DashboardAlertResponse]
