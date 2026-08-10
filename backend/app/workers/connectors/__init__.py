from app.workers.connectors.base import BaseConnector
from app.workers.connectors.vapi import VapiConnector
from app.workers.connectors.retell import RetellConnector
from app.workers.connectors.elevenlabs import ElevenLabsConnector
from app.workers.connectors.bolna import BolnaConnector

CONNECTORS = {
    "vapi": VapiConnector,
    "retell": RetellConnector,
    "elevenlabs": ElevenLabsConnector,
    "bolna": BolnaConnector
}

__all__ = [
    "BaseConnector",
    "VapiConnector",
    "RetellConnector",
    "ElevenLabsConnector",
    "BolnaConnector",
    "CONNECTORS"
]
