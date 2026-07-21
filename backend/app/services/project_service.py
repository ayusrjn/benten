import logging
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.organization import Organization, Member
from app.models.project import Project
from app.models.integration import Integration

logger = logging.getLogger(__name__)

PROVIDER_KEY_TO_NAME = {
    "elevenlabs": "ElevenLabs",
    "vapi": "Vapi",
    "retell": "Retell"
}

PROVIDER_NAME_TO_KEY = {v: k for k, v in PROVIDER_KEY_TO_NAME.items()}


class ProjectService:
    @staticmethod
    def get_or_create_user_project(db: Session, user: User) -> Project:
        """
        Resolves or provisions the Organization, Member, Project, and default Integrations for a user.
        """
        # 1. Resolve organization via Member email
        member = db.query(Member).filter(Member.email == user.email).first()
        
        if not member:
            # Auto-create Organization for user
            org_name = f"{user.email.split('@')[0]}'s Org" if user.email else "Default Org"
            org = Organization(name=org_name)
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

    @staticmethod
    def get_user_member(db: Session, user: User) -> Member | None:
        return db.query(Member).filter(Member.email == user.email).first()
