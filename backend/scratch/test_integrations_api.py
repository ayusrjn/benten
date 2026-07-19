import sys
import os

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, Member
from app.models.project import Project
from app.models.integration import Integration

client = TestClient(app)

def test_integrations_flow():
    db = SessionLocal()
    email = "api_test_user@example.com"
    password = "testpassword123"
    
    try:
        # Clean up existing test user if any
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            db.delete(existing_user)
            db.commit()
            
        print("1. Registering test user...")
        reg_response = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "API Test User"
        })
        assert reg_response.status_code == 200, f"Registration failed: {reg_response.text}"
        print("✓ Registered successfully!")

        print("\n2. Logging in to get JWT token...")
        login_response = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": password
        })
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✓ Logged in and received token!")

        print("\n3. Testing GET /api/v1/integrations (Initial state)...")
        get_response = client.get("/api/v1/integrations", headers=headers)
        assert get_response.status_code == 200, f"GET integrations failed: {get_response.text}"
        data = get_response.json()
        assert len(data) == 4, f"Expected 4 standard integrations, got {len(data)}"
        for item in data:
            assert item["connected"] is False, f"Expected disconnected state initially, got connected={item['connected']}"
            assert item["apiKey"] == "", f"Expected empty apiKey initially, got '{item['apiKey']}'"
        print("✓ Received all 4 integrations, all disconnected as expected!")

        print("\n4. Testing PUT /api/v1/integrations/vapi (Connect Vapi)...")
        put_response = client.put("/api/v1/integrations/vapi", headers=headers, json={
            "apiKey": "sk-vapi-live-9876543210",
            "webhookUrl": "https://callback.mycompany.com/vapi"
        })
        assert put_response.status_code == 200, f"PUT integration failed: {put_response.text}"
        vapi_data = put_response.json()
        assert vapi_data["connected"] is True
        assert vapi_data["apiKey"] == "••••••••••••••••••••••••3210"
        assert vapi_data["webhookUrl"] == "https://callback.mycompany.com/vapi"
        print("✓ Vapi connected and config saved successfully!")

        print("\n5. Testing GET /api/v1/integrations (Verify persistence)...")
        get_response2 = client.get("/api/v1/integrations", headers=headers)
        assert get_response2.status_code == 200
        data2 = get_response2.json()
        vapi_item = next(item for item in data2 if item["id"] == "vapi")
        assert vapi_item["connected"] is True
        assert vapi_item["apiKey"] == "••••••••••••••••••••••••3210"
        assert vapi_item["webhookUrl"] == "https://callback.mycompany.com/vapi"
        print("✓ GET list confirms Vapi integration is connected!")

        print("\n6. Testing PUT with masked key (Should not overwrite database key)...")
        put_response2 = client.put("/api/v1/integrations/vapi", headers=headers, json={
            "apiKey": "••••••••••••••••••••••••3210",  # Masked key
            "webhookUrl": "https://callback.mycompany.com/vapi-updated"
        })
        assert put_response2.status_code == 200
        vapi_data2 = put_response2.json()
        assert vapi_data2["connected"] is True
        assert vapi_data2["webhookUrl"] == "https://callback.mycompany.com/vapi-updated"
        
        # Verify database record still has original unmasked key
        user_record = db.query(User).filter(User.email == email).first()
        member_record = db.query(Member).filter(Member.email == email).first()
        project_record = db.query(Project).filter(Project.organization_id == member_record.organization_id).first()
        db_integration = db.query(Integration).filter(
            Integration.project_id == project_record.id,
            Integration.name == "Vapi"
        ).first()
        assert db_integration.api_key == "sk-vapi-live-9876543210", f"Key was overwritten! Got: {db_integration.api_key}"
        print("✓ Successfully ignored masked key update and preserved the real key in the DB!")

        print("\n7. Testing Disconnect (Sending empty apiKey)...")
        put_response3 = client.put("/api/v1/integrations/vapi", headers=headers, json={
            "apiKey": "",
            "webhookUrl": ""
        })
        assert put_response3.status_code == 200
        vapi_data3 = put_response3.json()
        assert vapi_data3["connected"] is False
        assert vapi_data3["apiKey"] == ""
        assert vapi_data3["webhookUrl"] is None
        print("✓ Vapi disconnected successfully!")

        print("\n🎉 Integrations API endpoints flow verified successfully!")

    finally:
        # Cleanup user and cascade dependencies
        user_record = db.query(User).filter(User.email == email).first()
        if user_record:
            db.delete(user_record)
            
        member_record = db.query(Member).filter(Member.email == email).first()
        if member_record:
            org_record = db.query(Organization).filter(Organization.id == member_record.organization_id).first()
            if org_record:
                db.delete(org_record)
                
        db.commit()
        db.close()

if __name__ == "__main__":
    test_integrations_flow()
