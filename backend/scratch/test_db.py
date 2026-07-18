import sys
import os

# Add backend root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models import Organization, Member, Project, Agent, Conversation, SpeechSegment, AlertRule, Alert, Integration

def test_relations():
    db = SessionLocal()
    try:
        print("1. Creating dummy records...")
        org = Organization(name="Test Org")
        db.add(org)
        db.commit()
        db.refresh(org)
        print(f"Created Org: {org.name} ({org.id})")

        member = Member(organization_id=org.id, email="test@example.com", role="Owner")
        db.add(member)

        project = Project(organization_id=org.id, name="Test Project")
        db.add(project)
        db.commit()
        db.refresh(project)
        print(f"Created Project: {project.name} ({project.id})")

        agent = Agent(project_id=project.id, name="Test Agent", provider="Vapi")
        db.add(agent)
        db.commit()
        db.refresh(agent)
        print(f"Created Agent: {agent.name} ({agent.id})")

        conv = Conversation(
            project_id=project.id,
            agent_id=agent.id,
            duration_sec=120,
            status="Healthy",
            health_score=95,
            latency_ms=250,
            dead_air_percent=5.5,
            interruptions=2,
            speech_rate_wpm=130,
            primary_emotion="Calm",
            voice_quality=88,
            audio_url="http://example.com/audio.wav",
            raw_metrics_json={"tts_latency": 150}
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        print(f"Created Conversation: {conv.id}")

        seg = SpeechSegment(
            conversation_id=conv.id,
            speaker="agent",
            start_sec=1.5,
            end_sec=5.0,
            text="Hello, how can I help you today?"
        )
        db.add(seg)

        rule = AlertRule(
            project_id=project.id,
            metric="Average Latency",
            threshold="> 2s",
            duration="1 conversation",
            action="Send Slack"
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        alert = Alert(
            project_id=project.id,
            alert_rule_id=rule.id,
            conversation_id=conv.id,
            status="Triggered"
        )
        db.add(alert)

        integration = Integration(
            project_id=project.id,
            name="Vapi",
            connected=True,
            api_key="secret-api-key",
            config={"api_url": "https://api.vapi.ai"}
        )
        db.add(integration)
        db.commit()

        print("\n2. Querying and validating relationships...")
        # Reload Project
        db.refresh(project)
        assert len(project.agents) == 1, "Agent relation failed"
        assert len(project.conversations) == 1, "Conversation relation failed"
        assert len(project.alert_rules) == 1, "AlertRule relation failed"
        assert len(project.alerts) == 1, "Alert relation failed"
        assert len(project.integrations) == 1, "Integration relation failed"
        print("✓ Project relations load successfully!")

        # Reload Org
        db.refresh(org)
        assert len(org.projects) == 1, "Org -> Projects relation failed"
        assert len(org.members) == 1, "Org -> Members relation failed"
        print("✓ Organization relations load successfully!")

        # Reload Conversation
        db.refresh(conv)
        assert len(conv.speech_segments) == 1, "SpeechSegments relation failed"
        assert conv.speech_segments[0].text == "Hello, how can I help you today?", "SpeechSegment text mismatch"
        print("✓ SpeechSegment matches conversation!")

        print("\n3. Testing cascading deletes on Project...")
        db.delete(project)
        db.commit()

        # Verify that agents, conversations, alert_rules, integrations are deleted
        assert db.get(Agent, agent.id) is None, "Agent was not deleted"
        assert db.get(Conversation, conv.id) is None, "Conversation was not deleted"
        assert db.get(AlertRule, rule.id) is None, "AlertRule was not deleted"
        assert db.get(Integration, integration.id) is None, "Integration was not deleted"
        # Alert should be deleted as it belongs to project
        assert db.get(Alert, alert.id) is None, "Alert was not deleted"
        # Speech segments should be deleted because conversation was deleted
        assert db.query(SpeechSegment).filter_by(conversation_id=conv.id).first() is None, "SpeechSegment was not deleted"
        print("✓ Cascade deletes on Project worked perfectly!")

        print("\n4. Testing cascading deletes on Organization...")
        db.delete(org)
        db.commit()

        assert db.get(Member, member.id) is None, "Member was not deleted"
        print("✓ Cascade deletes on Organization worked perfectly!")

        print("\n🎉 All database tests passed successfully!")

    except Exception as e:
        db.rollback()
        print(f"❌ Test failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_relations()
