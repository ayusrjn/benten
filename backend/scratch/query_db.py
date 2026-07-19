import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Member
from app.models.project import Project
from app.models.integration import Integration

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "user@example.com").first()
    if not user:
        print("User user@example.com not found")
    else:
        print(f"User: {user.email}")
        member = db.query(Member).filter(Member.email == user.email).first()
        if not member:
            print("Member not found")
        else:
            print(f"Member Org ID: {member.organization_id}")
            project = db.query(Project).filter(Project.organization_id == member.organization_id).first()
            if not project:
                print("Project not found")
            else:
                print(f"Project ID: {project.id}, Name: {project.name}")
                integrations = db.query(Integration).filter(Integration.project_id == project.id).all()
                print(f"Number of integrations: {len(integrations)}")
                for i in integrations:
                    print(f" - {i.name}: connected={i.connected}, key={i.api_key}, webhook={i.webhook_url}")
finally:
    db.close()
