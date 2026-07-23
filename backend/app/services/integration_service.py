import logging
import requests
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.integration import Integration
from app.models.agent import Agent
from app.api.security_crypto import encrypt_secret, decrypt_secret
from app.services.project_service import PROVIDER_KEY_TO_NAME
from app.workers.tasks import CONNECTORS

logger = logging.getLogger(__name__)

PROVIDER_CONFS = {
    "vapi": {
        "url": "https://api.vapi.ai/assistant",
        "method": "GET",
        "headers": lambda key: {"Authorization": f"Bearer {key}"},
        "params": {"limit": 1}
    },
    "retell": {
        "url": "https://api.retellai.com/v3/list-calls",
        "method": "POST",
        "headers": lambda key: {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        "json": {}
    },
    "elevenlabs": {
        "url": "https://api.elevenlabs.io/v1/convai/agents",
        "method": "GET",
        "headers": lambda key: {"xi-api-key": key}
    }
}


class IntegrationService:
    @staticmethod
    def verify_api_key(provider_id: str, api_key: str) -> Tuple[bool, str]:
        provider_name = PROVIDER_KEY_TO_NAME.get(provider_id.lower())
        if not provider_name:
            return False, f"Integration provider '{provider_id}' not found"

        if api_key == "mock" or api_key.startswith("mock_"):
            return True, f"Successfully connected to Mock {provider_name} service!"

        pid = provider_id.lower()
        if pid not in PROVIDER_CONFS:
            return True, f"Connection parameters valid for {provider_name}"

        conf = PROVIDER_CONFS[pid]
        try:
            res = requests.request(
                method=conf["method"],
                url=conf["url"],
                headers=conf["headers"](api_key),
                params=conf.get("params"),
                json=conf.get("json"),
                timeout=10
            )
            if res.status_code == 200:
                return True, f"Successfully connected to {provider_name} API!"
            if res.status_code in (401, 403):
                return False, "Invalid API key or unauthorized access."
            return False, f"Provider API returned error status: {res.status_code}"
        except Exception as e:
            return False, f"Failed to connect to provider: {str(e)}"

    @staticmethod
    def get_decrypted_key(integration: Integration) -> Optional[str]:
        if not integration or not integration.api_key:
            return None
        return decrypt_secret(integration.api_key)

    @staticmethod
    def mask_api_key(raw_key: str | None) -> str:
        if not raw_key:
            return ""
        decrypted = decrypt_secret(raw_key) or ""
        if len(decrypted) <= 4:
            return "••••••••••••"
        return "••••••••••••••••••••••••" + decrypted[-4:]

    @staticmethod
    def save_integration_key(db: Session, integration: Integration, raw_api_key: str | None):
        if raw_api_key is None or raw_api_key.strip() == "":
            integration.api_key = None
            integration.connected = False
        else:
            integration.api_key = encrypt_secret(raw_api_key.strip())
            integration.connected = True
        db.commit()

    @staticmethod
    def sync_agents(db: Session, project_id: Any, provider: str, raw_api_key: str) -> List[Agent]:
        provider_key = provider.lower()
        connector_cls = CONNECTORS.get(provider_key)
        if not connector_cls:
            logger.warning(f"No connector found for provider {provider}")
            return []

        try:
            connector = connector_cls(api_key=raw_api_key)
            raw_agents = connector.list_agents()
        except Exception as e:
            logger.exception(f"Failed to list agents for provider {provider}: {e}")
            return []

        synced_agents = []
        now = datetime.now(timezone.utc)

        for item in raw_agents:
            ext_id = item.get("external_id")
            name = item.get("name") or f"{provider.capitalize()} Agent"
            desc = item.get("description")
            raw_meta = item.get("raw_metadata")

            agent = None
            if ext_id:
                agent = db.query(Agent).filter(
                    Agent.project_id == project_id,
                    Agent.provider == provider_key,
                    Agent.external_id == ext_id
                ).first()

            if not agent:
                agent = db.query(Agent).filter(
                    Agent.project_id == project_id,
                    Agent.provider == provider_key,
                    Agent.name == name
                ).first()

            if agent:
                agent.name = name
                agent.external_id = ext_id or agent.external_id
                agent.description = desc or agent.description
                agent.raw_metadata = raw_meta or agent.raw_metadata
                agent.last_synced_at = now
            else:
                agent = Agent(
                    project_id=project_id,
                    name=name,
                    provider=provider_key,
                    external_id=ext_id,
                    description=desc,
                    raw_metadata=raw_meta,
                    last_synced_at=now
                )
                db.add(agent)

            synced_agents.append(agent)

        db.commit()
        return synced_agents
