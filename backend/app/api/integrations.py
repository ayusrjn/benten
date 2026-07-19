from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.organization import Organization, Member
from app.models.integration import Integration

router = APIRouter(prefix="/integrations", tags=["Integrations"])

PROVIDER_KEY_TO_NAME = {
    "elevenlabs": "ElevenLabs",
    "vapi": "Vapi",
    "retell": "Retell"
}

PROVIDER_NAME_TO_KEY = {v: k for k, v in PROVIDER_KEY_TO_NAME.items()}


def verify_api_key(provider_id: str, api_key: str) -> tuple[bool, str]:
    provider_name = PROVIDER_KEY_TO_NAME.get(provider_id.lower())
    if not provider_name:
        return False, f"Integration provider '{provider_id}' not found"

    if api_key == "mock" or api_key.startswith("mock_"):
        return True, f"Successfully connected to Mock {provider_name} service!"

    try:
        import requests
        if provider_id.lower() == "vapi":
            url = "https://api.vapi.ai/assistant"
            headers = {"Authorization": f"Bearer {api_key}"}
            res = requests.get(url, headers=headers, params={"limit": 1}, timeout=10)
        elif provider_id.lower() == "retell":
            url = "https://api.retellai.com/v3/list-calls"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            res = requests.post(url, headers=headers, json={}, timeout=10)
        elif provider_id.lower() == "elevenlabs":
            url = "https://api.elevenlabs.io/v1/convai/agents"
            headers = {"xi-api-key": api_key}
            res = requests.get(url, headers=headers, timeout=10)
        else:
            return True, f"Connection parameters valid for {provider_name}"

        if res.status_code == 200:
            return True, f"Successfully connected to {provider_name} API!"
        elif res.status_code in (401, 403):
            return False, "Invalid API key or unauthorized access."
        else:
            return False, f"Provider API returned error status: {res.status_code}"

    except Exception as e:
        return False, f"Failed to connect to provider: {str(e)}"

class IntegrationResponse(BaseModel):
    id: str  # lowercase provider key
    name: str  # e.g., 'Vapi'
    connected: bool
    apiKey: str
    webhookUrl: Optional[str] = None
    config: Optional[dict] = None

    class Config:
        from_attributes = True

class IntegrationUpdate(BaseModel):
    apiKey: Optional[str] = None
    webhookUrl: Optional[str] = None

def get_or_create_user_project(db: Session, user: User) -> Project:
    # 1. Resolve organization via Member email
    member = db.query(Member).filter(Member.email == user.email).first()
    
    if not member:
        # Auto-create Organization for user
        org = Organization(name=f"{user.email.split('@')[0]}'s Org")
        db.add(org)
        db.commit()
        db.refresh(org)
        
        # Auto-create Member entry
        member = Member(organization_id=org.id, email=user.email, role="Owner")
        db.add(member)
        db.commit()
        db.refresh(member)
        
    # 2. Resolve Project under this organization
    project = db.query(Project).filter(Project.organization_id == member.organization_id).first()
    
    if not project:
        # Auto-create default Project
        project = Project(organization_id=member.organization_id, name="Default Project")
        db.add(project)
        db.commit()
        db.refresh(project)
        
    # 3. Seed integration placeholders
    for key, name in PROVIDER_KEY_TO_NAME.items():
        integration = db.query(Integration).filter(
            Integration.project_id == project.id,
            Integration.name == name
        ).first()
        
        if not integration:
            integration = Integration(
                project_id=project.id,
                name=name,
                connected=False,
                api_key=None,
                webhook_url=None,
                config={}
            )
            db.add(integration)
            
    db.commit()
    db.refresh(project)
    return project

@router.get("", response_model=List[IntegrationResponse])
def list_integrations(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    integrations = db.query(Integration).filter(Integration.project_id == project.id).all()
    
    response_list = []
    for integration in integrations:
        provider_key = PROVIDER_NAME_TO_KEY.get(integration.name)
        if not provider_key:
            continue
            
        # Mask the API key
        masked_key = ""
        if integration.api_key:
            masked_key = "••••••••••••••••••••••••" + integration.api_key[-4:]
            
        response_list.append(IntegrationResponse(
            id=provider_key,
            name=integration.name,
            connected=integration.connected,
            apiKey=masked_key,
            webhookUrl=integration.webhook_url,
            config=integration.config
        ))
        
    response.headers["x-total-count"] = str(len(response_list))
    return response_list

@router.get("/{id}", response_model=IntegrationResponse)
def get_integration(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    masked_key = ""
    if integration.api_key:
        masked_key = "••••••••••••••••••••••••" + integration.api_key[-4:]
        
    return IntegrationResponse(
        id=id.lower(),
        name=integration.name,
        connected=integration.connected,
        apiKey=masked_key,
        webhookUrl=integration.webhook_url,
        config=integration.config
    )

from datetime import datetime, timezone
import logging

from app.models.agent import Agent
from app.workers.tasks import CONNECTORS

logger = logging.getLogger(__name__)

def sync_agents_for_integration(db: Session, project_id, provider: str, api_key: str) -> List[Agent]:
    """
    Fetches agent list from provider connector and upserts into agents database table.
    """
    provider_key = provider.lower()
    connector_cls = CONNECTORS.get(provider_key)
    if not connector_cls:
        logger.warning(f"No connector found for provider {provider}")
        return []

    try:
        connector = connector_cls(api_key=api_key)
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

        # Lookup existing agent by project, provider, external_id or name
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


@router.put("/{id}", response_model=IntegrationResponse)
@router.patch("/{id}", response_model=IntegrationResponse)
def update_integration(
    id: str,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    newly_connected = False
    active_key = integration.api_key

    # Apply updates
    if payload.apiKey is not None:
        raw_key = payload.apiKey.strip()
        if not raw_key:
            # Disconnect
            integration.api_key = None
            integration.connected = False
            active_key = None
        elif "•" in raw_key:
            # Do not overwrite if they submitted the mask placeholder
            pass
        else:
            # New key entered - Validate it
            success, msg = verify_api_key(id, raw_key)
            if not success:
                raise HTTPException(status_code=400, detail=f"API key connection test failed: {msg}")
            integration.api_key = raw_key
            integration.connected = True
            active_key = raw_key
            newly_connected = True
            
    if payload.webhookUrl is not None:
        integration.webhook_url = payload.webhookUrl.strip() or None
        
    db.commit()
    db.refresh(integration)
    
    # Auto-sync agents if connected
    if integration.connected and active_key:
        sync_agents_for_integration(db, project.id, id, active_key)

    masked_key = ""
    if integration.api_key:
        masked_key = "••••••••••••••••••••••••" + integration.api_key[-4:]
        
    return IntegrationResponse(
        id=id.lower(),
        name=integration.name,
        connected=integration.connected,
        apiKey=masked_key,
        webhookUrl=integration.webhook_url,
        config=integration.config
    )


class TestConnectionRequest(BaseModel):
    apiKey: str


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


@router.post("/{id}/test", response_model=TestConnectionResponse)
def test_integration_connection(
    id: str,
    payload: TestConnectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    api_key = payload.apiKey.strip()
    if not api_key:
        return TestConnectionResponse(success=False, message="API key cannot be empty")
        
    # Handle masked key by resolving stored api_key
    if "•" in api_key:
        integration = db.query(Integration).filter(
            Integration.project_id == project.id,
            Integration.name == provider_name
        ).first()
        if integration and integration.api_key:
            api_key = integration.api_key
        else:
            return TestConnectionResponse(success=False, message="No API key stored to test.")

    success, msg = verify_api_key(id, api_key)
    return TestConnectionResponse(success=success, message=msg)


class SyncAgentsResponse(BaseModel):
    success: bool
    count: int
    message: str


@router.post("/{id}/sync-agents", response_model=SyncAgentsResponse)
def sync_integration_agents(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")

    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()

    if not integration or not integration.connected or not integration.api_key:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' is not connected. Please enter an API key first.")

    agents = sync_agents_for_integration(db, project.id, id, integration.api_key)
    return SyncAgentsResponse(
        success=True,
        count=len(agents),
        message=f"Successfully synced {len(agents)} agents from {provider_name}"
    )

