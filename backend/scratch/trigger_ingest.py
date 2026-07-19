import sys
import os
import uuid

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import Organization, Project, Integration, Conversation, SpeechSegment, Agent
from app.workers.tasks import ingest_call
from app.workers import celery_app

def trigger_ingest_test():
    print("=== Benten Ingestion Verification Test ===")
    
    # 1. Enable Celery eager mode for fully synchronous testing
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    print("[*] Enabled Celery task_always_eager mode for synchronous test run.")

    db = SessionLocal()
    try:
        # 2. Seed a test organization and project
        print("[*] Seeding database with test organization and project...")
        org = db.query(Organization).filter(Organization.name == "Benten Verification Org").first()
        if not org:
            org = Organization(name="Benten Verification Org")
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"    Created Organization: {org.name} ({org.id})")
        else:
            print(f"    Found existing Organization: {org.name} ({org.id})")

        project = db.query(Project).filter(
            Project.organization_id == org.id,
            Project.name == "Verification Project"
        ).first()
        if not project:
            project = Project(organization_id=org.id, name="Verification Project")
            db.add(project)
            db.commit()
            db.refresh(project)
            print(f"    Created Project: {project.name} ({project.id})")
        else:
            print(f"    Found existing Project: {project.name} ({project.id})")

        # 3. Seed mock integrations if not present
        providers = ["vapi", "retell", "elevenlabs"]
        for p in providers:
            integration = db.query(Integration).filter(
                Integration.project_id == project.id,
                Integration.name == p
            ).first()
            if not integration:
                integration = Integration(
                    project_id=project.id,
                    name=p,
                    connected=True,
                    api_key="mock",
                    config={"api_url": f"https://api.{p}.com/mock"}
                )
                db.add(integration)
                print(f"    Seeded mock Integration for: {p}")
        db.commit()

        # Clean existing test conversations from prior runs to keep it clean
        existing_convs = db.query(Conversation).filter(Conversation.project_id == project.id).all()
        if existing_convs:
            print(f"[*] Cleaning up {len(existing_convs)} old test conversations...")
            for c in existing_convs:
                db.delete(c)
            db.commit()

        # 4. Trigger Ingestion tasks for each provider
        for p in providers:
            mock_call_id = f"mock_{p}_call_{uuid.uuid4().hex[:8]}"
            print(f"\n[*] Triggering ingestion for provider '{p}' (Call ID: {mock_call_id})...")
            
            # Since task_always_eager is True, this runs the task and the chained evaluate_audio task instantly!
            task_result = ingest_call.delay(str(project.id), p, mock_call_id)
            conversation_id = task_result.get()
            
            print(f"    [+] Ingestion task completed. Returned Conversation ID: {conversation_id}")
            
            # 5. Verify conversation and speech segments creation in PostgreSQL
            conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            assert conv is not None, f"Conversation {conversation_id} was not created!"
            assert conv.status == "Completed", f"Conversation status is '{conv.status}', expected 'Completed'!"
            assert conv.health_score == 92, f"Conversation health_score is {conv.health_score}, expected 92!"
            
            agent = db.query(Agent).filter(Agent.id == conv.agent_id).first()
            print(f"    [+] Verified Agent resolved/created: {agent.name} (Provider: {agent.provider})")
            print(f"    [+] Verified Conversation record updated:")
            print(f"        - Status: {conv.status}")
            print(f"        - Duration: {conv.duration_sec}s")
            print(f"        - Health Score: {conv.health_score}")
            print(f"        - Latency: {conv.latency_ms}ms")
            print(f"        - Dead Air: {conv.dead_air_percent}%")
            print(f"        - Primary Emotion: {conv.primary_emotion}")
            print(f"        - Voice Quality: {conv.voice_quality}")
            print(f"        - Audio URL: {conv.audio_url}")

            # Verify speech segments
            segments = db.query(SpeechSegment).filter(SpeechSegment.conversation_id == conv.id).order_by(SpeechSegment.start_sec).all()
            print(f"    [+] Verified Speech segments (turns: {len(segments)}):")
            for seg in segments:
                print(f"        [{seg.speaker} | {seg.start_sec}s - {seg.end_sec}s]: {seg.text[:50]}...")
            
            assert len(segments) > 0, "No speech segments created!"
            
        print("\n🎉 End-to-end sync verification tests passed successfully!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Test failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    trigger_ingest_test()
