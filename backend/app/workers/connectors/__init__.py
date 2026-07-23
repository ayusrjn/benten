from app.workers.connectors.base import BaseConnector
from app.workers.connectors.vapi import VapiConnector
from app.workers.connectors.retell import RetellConnector
from app.workers.connectors.elevenlabs import ElevenLabsConnector

CONNECTORS = {
    "vapi": VapiConnector,
    "retell": RetellConnector,
    "elevenlabs": ElevenLabsConnector
}

__all__ = [
    "BaseConnector",
    "VapiConnector",
    "RetellConnector",
    "ElevenLabsConnector",
    "CONNECTORS"
]
