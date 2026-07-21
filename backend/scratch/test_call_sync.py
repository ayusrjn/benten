import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone
from app.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.integration import Integration
from app.models.conversation import Conversation, SpeechSegment
from app.workers.connectors.elevenlabs import ElevenLabsConnector
from app.workers.connectors.vapi import VapiConnector
from app.workers.connectors.retell import RetellConnector
from app.workers.tasks import sync_calls_for_integration
from app.services.project_service import ProjectService


def run_call_sync_tests():
    print("=== STARTING CALL SYNCHRONIZATION INTEGRATION TESTS ===")
    db = SessionLocal()

    try:
        # 1. Setup Test User and Project
        test_email = "sync_tester@benten.ai"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            user = User(email=test_email, hashed_password="dummy_hash", full_name="Test User")
            db.add(user)
            db.commit()
            db.refresh(user)

        project = ProjectService.get_or_create_user_project(db, user)
        print(f"[1] Verified test project: '{project.name}' (ID: {project.id})")

        # 2. Test Connector Interfaces in Mock Mode
        providers = ["elevenlabs", "vapi", "retell"]
        connectors = {
            "elevenlabs": ElevenLabsConnector(api_key="mock"),
            "vapi": VapiConnector(api_key="mock"),
            "retell": RetellConnector(api_key="mock")
        }

        for prov, conn in connectors.items():
            valid, msg = conn.verify_key()
            assert valid, f"{prov} verify_key failed"
            
            calls = conn.list_calls()
            assert len(calls) > 0, f"{prov} list_calls returned empty list"
            
            first_call_id = calls[0]["external_id"]
            details = conn.get_call(first_call_id)
            assert details["external_id"] == first_call_id
            assert "turns" in details
            print(f"[2] Connector '{prov}' verified: {len(calls)} calls listed, get_call('{first_call_id}') returned {len(details['turns'])} turns.")

        # 3. Connect Integrations in DB with Mock Keys
        for prov_key in providers:
            name_map = {"elevenlabs": "ElevenLabs", "vapi": "Vapi", "retell": "Retell"}
            prov_name = name_map[prov_key]
            
            integration = db.query(Integration).filter(
                Integration.project_id == project.id,
                Integration.name == prov_name
            ).first()
            
            if not integration:
                integration = Integration(project_id=project.id, name=prov_name)
                db.add(integration)

            integration.connected = True
            integration.api_key = "mock"
            integration.last_synced_at = None
            db.commit()

        print("[3] Seeded active mock integrations in DB")

        # 4. Perform Initial Sync for all providers
        for prov_key in providers:
            res = sync_calls_for_integration(db, str(project.id), prov_key)
            print(f"[4.1] Initial sync for '{prov_key}': total={res['total']}, imported={res['imported']}, skipped={res['skipped']}")
            assert res["imported"] > 0, f"Expected imported > 0 for {prov_key}"
            assert res["skipped"] == 0, f"Expected skipped == 0 for initial sync of {prov_key}"

        # 5. Test Deduplication Logic (Re-running sync immediately)
        for prov_key in providers:
            res_repeat = sync_calls_for_integration(db, str(project.id), prov_key)
            print(f"[5] Re-sync for '{prov_key}': total={res_repeat['total']}, imported={res_repeat['imported']}, skipped={res_repeat['skipped']}")
            assert res_repeat["imported"] == 0, f"Expected 0 new imports on repeat sync for {prov_key}"
            assert res_repeat["skipped"] == res_repeat["total"], f"Expected all calls skipped on repeat sync for {prov_key}"

        # 6. Verify Database Persistence & Attributes
        conversations = db.query(Conversation).filter(Conversation.project_id == project.id).all()
        print(f"[6] Total conversations saved in DB for project: {len(conversations)}")
        assert len(conversations) >= 6, "Expected at least 6 conversations stored across providers"

        for conv in conversations:
            assert conv.external_id is not None
            assert conv.provider in providers
            assert conv.duration_sec > 0
            
            segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conv.id).all()
            assert len(segments) > 0, f"Conversation {conv.id} ({conv.provider}) should have speech segments"
            print(f"    - [{conv.provider.upper()}] Call ID: {conv.external_id} | Duration: {conv.duration_sec}s | Cost: ${conv.cost} | Segments: {len(segments)}")

        # 7. Check Last Synced At Timestamps
        for prov_name in ["ElevenLabs", "Vapi", "Retell"]:
            integ = db.query(Integration).filter(Integration.project_id == project.id, Integration.name == prov_name).first()
            assert integ.last_synced_at is not None, f"Integration {prov_name} missing last_synced_at timestamp"
            print(f"[7] Integration '{prov_name}' last_synced_at: {integ.last_synced_at.isoformat()}")

        print("\nALL CALL SYNCHRONIZATION TESTS PASSED SUCCESSFULLY! ")

    except Exception as e:
        print(f"\n TEST FAILED WITH EXCEPTION: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_call_sync_tests()
