from sqlalchemy.orm import Session
from app.models.user import User
from app.models.organization import Organization, Member
from app.models.project import Project
from app.models.integration import Integration

PROVIDER_KEY_TO_NAME = {
    "elevenlabs": "ElevenLabs",
    "vapi": "Vapi",
    "retell": "Retell",
    "bolna": "Bolna"
}

PROVIDER_NAME_TO_KEY = {v: k for k, v in PROVIDER_KEY_TO_NAME.items()}


class ProjectService:
    @staticmethod
    def get_or_create_user_project(db: Session, user: User) -> Project:
        member = db.query(Member).filter(Member.email == user.email).first()
        
        if not member:
            org_name = f"{user.email.split('@')[0]}'s Org" if user.email else "Default Org"
            org = Organization(name=org_name)
            db.add(org)
            db.flush()
            
            member = Member(organization_id=org.id, email=user.email, role="Owner")
            db.add(member)
            db.flush()
            
        project = db.query(Project).filter(Project.organization_id == member.organization_id).first()
        
        if not project:
            project = Project(organization_id=member.organization_id, name="Default Project")
            db.add(project)
            db.flush()
            
        for name in PROVIDER_KEY_TO_NAME.values():
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
