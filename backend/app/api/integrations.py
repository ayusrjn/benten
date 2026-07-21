import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.security import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.integration import Integration
from app.services.project_service import ProjectService, PROVIDER_KEY_TO_NAME, PROVIDER_NAME_TO_KEY
from app.services.integration_service import IntegrationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class IntegrationResponse(BaseModel):
    id: str  # lowercase provider key
    name: str  # e.g., 'Vapi'
    connected: bool
    apiKey: str
    webhookUrl: Optional[str] = None
    config: Optional[dict] = None
    lastSyncedAt: Optional[str] = None

    class Config:
        from_attributes = True


class IntegrationUpdate(BaseModel):
    apiKey: Optional[str] = None
    webhookUrl: Optional[str] = None


# Backward compatibility helper functions
def get_or_create_user_project(db: Session, user: User) -> Project:
    return ProjectService.get_or_create_user_project(db, user)


def verify_api_key(provider_id: str, api_key: str) -> tuple[bool, str]:
    return IntegrationService.verify_api_key(provider_id, api_key)


def sync_agents_for_integration(db: Session, project_id, provider: str, api_key: str):
    return IntegrationService.sync_agents(db, project_id, provider, api_key)


@router.get("", response_model=List[IntegrationResponse])
def list_integrations(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    integrations = db.query(Integration).filter(Integration.project_id == project.id).all()
    
    response_list = []
    for integration in integrations:
        provider_key = PROVIDER_NAME_TO_KEY.get(integration.name)
        if not provider_key:
            continue
            
        masked_key = IntegrationService.mask_api_key(integration.api_key)
        last_synced_str = integration.last_synced_at.isoformat() if integration.last_synced_at else None

        response_list.append(IntegrationResponse(
            id=provider_key,
            name=integration.name,
            connected=integration.connected,
            apiKey=masked_key,
            webhookUrl=integration.webhook_url,
            config=integration.config,
            lastSyncedAt=last_synced_str
        ))
        
    response.headers["x-total-count"] = str(len(response_list))
    return response_list


@router.get("/{id}", response_model=IntegrationResponse)
def get_integration(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    masked_key = IntegrationService.mask_api_key(integration.api_key)
    last_synced_str = integration.last_synced_at.isoformat() if integration.last_synced_at else None

    return IntegrationResponse(
        id=id.lower(),
        name=integration.name,
        connected=integration.connected,
        apiKey=masked_key,
        webhookUrl=integration.webhook_url,
        config=integration.config,
        lastSyncedAt=last_synced_str
    )


@router.put("/{id}", response_model=IntegrationResponse)
@router.patch("/{id}", response_model=IntegrationResponse)
def update_integration(
    id: str,
    payload: IntegrationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    raw_api_key = None

    if payload.apiKey is not None:
        raw_key = payload.apiKey.strip()
        if not raw_key:
            IntegrationService.save_integration_key(db, integration, None)
        elif "•" in raw_key:
            # Mask placeholder submitted; keep existing key
            raw_api_key = IntegrationService.get_decrypted_key(integration)
        else:
            success, msg = IntegrationService.verify_api_key(id, raw_key)
            if not success:
                raise HTTPException(status_code=400, detail=f"API key connection test failed: {msg}")
            IntegrationService.save_integration_key(db, integration, raw_key)
            raw_api_key = raw_key

    if payload.webhookUrl is not None:
        integration.webhook_url = payload.webhookUrl.strip() or None
        db.commit()
        
    db.refresh(integration)
    
    # Auto-sync agents if connected
    if integration.connected:
        if not raw_api_key:
            raw_api_key = IntegrationService.get_decrypted_key(integration)
        if raw_api_key:
            IntegrationService.sync_agents(db, project.id, id, raw_api_key)

    masked_key = IntegrationService.mask_api_key(integration.api_key)
    last_synced_str = integration.last_synced_at.isoformat() if integration.last_synced_at else None

    return IntegrationResponse(
        id=id.lower(),
        name=integration.name,
        connected=integration.connected,
        apiKey=masked_key,
        webhookUrl=integration.webhook_url,
        config=integration.config,
        lastSyncedAt=last_synced_str
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
    project = ProjectService.get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")
        
    api_key = payload.apiKey.strip()
    if not api_key:
        return TestConnectionResponse(success=False, message="API key cannot be empty")
        
    if "•" in api_key:
        integration = db.query(Integration).filter(
            Integration.project_id == project.id,
            Integration.name == provider_name
        ).first()
        decrypted = IntegrationService.get_decrypted_key(integration)
        if decrypted:
            api_key = decrypted
        else:
            return TestConnectionResponse(success=False, message="No API key stored to test.")

    success, msg = IntegrationService.verify_api_key(id, api_key)
    return TestConnectionResponse(success=success, message=msg)


class SyncAgentsResponse(BaseModel):
    success: bool
    count: int
    message: str


@router.post("/{id}/sync-agents", response_model=SyncAgentsResponse)
def sync_integration_agents_route(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")

    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()

    if not integration or not integration.connected or not integration.api_key:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' is not connected. Please enter an API key first.")

    raw_api_key = IntegrationService.get_decrypted_key(integration)
    agents = IntegrationService.sync_agents(db, project.id, id, raw_api_key)
    return SyncAgentsResponse(
        success=True,
        count=len(agents),
        message=f"Successfully synced {len(agents)} agents from {provider_name}"
    )


class SyncCallsResponse(BaseModel):
    success: bool
    total: int
    imported: int
    skipped: int
    message: str


@router.post("/{id}/sync-calls", response_model=SyncCallsResponse)
def sync_integration_calls_route(
    id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = ProjectService.get_or_create_user_project(db, current_user)
    provider_name = PROVIDER_KEY_TO_NAME.get(id.lower())
    if not provider_name:
        raise HTTPException(status_code=404, detail=f"Integration provider '{id}' not found")

    integration = db.query(Integration).filter(
        Integration.project_id == project.id,
        Integration.name == provider_name
    ).first()

    if not integration or not integration.connected or not integration.api_key:
        raise HTTPException(status_code=400, detail=f"Provider '{provider_name}' is not connected. Please enter an API key first.")

    from app.workers.tasks import sync_calls_for_integration
    result = sync_calls_for_integration(db, str(project.id), id.lower())
    
    return SyncCallsResponse(
        success=True,
        total=result["total"],
        imported=result["imported"],
        skipped=result["skipped"],
        message=f"Sync completed for {provider_name}: {result['imported']} imported, {result['skipped']} skipped out of {result['total']} calls."
    )
