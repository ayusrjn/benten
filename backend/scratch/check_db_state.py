import sys
import os

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, Member
from app.models.project import Project
from app.models.integration import Integration

def check_db():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"--- Users ({len(users)}) ---")
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, Active: {u.is_active}")

        members = db.query(Member).all()
        print(f"\n--- Members ({len(members)}) ---")
        for m in members:
            print(f"ID: {m.id}, OrgID: {m.organization_id}, Email: {m.email}, Role: {m.role}")

        orgs = db.query(Organization).all()
        print(f"\n--- Organizations ({len(orgs)}) ---")
        for o in orgs:
            print(f"ID: {o.id}, Name: {o.name}")

        projects = db.query(Project).all()
        print(f"\n--- Projects ({len(projects)}) ---")
        for p in projects:
            print(f"ID: {p.id}, OrgID: {p.organization_id}, Name: {p.name}")

        integrations = db.query(Integration).all()
        print(f"\n--- Integrations ({len(integrations)}) ---")
        for i in integrations:
            print(f"ID: {i.id}, ProjectID: {i.project_id}, Name: {i.name}, Connected: {i.connected}, Key: {i.api_key}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_db()
