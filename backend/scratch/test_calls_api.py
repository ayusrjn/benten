import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.conversation import Conversation
from app.models.project import Project
from app.api.integrations import get_or_create_user_project
from app.api.conversations import map_conversation_to_response, calculate_grade


def test_calls_api():
    print("=== TESTING CALLS BACKEND API ENHANCEMENTS ===")
    db = SessionLocal()

    try:
        # 1. Fetch user and project
        user = db.query(User).first()
        assert user is not None, "User expected in DB"

        project = get_or_create_user_project(db, user)
        print(f"[1] Active user: {user.email} | Project: {project.name}")

        # 2. Fetch conversations
        conversations = db.query(Conversation).filter(Conversation.project_id == project.id).all()
        print(f"[2] Found {len(conversations)} conversations in DB")
        assert len(conversations) > 0, "Expected at least 1 conversation stored"

        # 3. Test Response Mapping
        sample_conv = conversations[0]
        res = map_conversation_to_response(db, sample_conv)

        print(f"[3] Sample Call Mapped Response:")
        print(f"    - ID: {res.id}")
        print(f"    - Provider: {res.provider}")
        print(f"    - External ID: {res.externalId}")
        print(f"    - Agent Name: {res.agentName}")
        print(f"    - Score: {res.score} | Grade: {res.grade}")
        print(f"    - Duration: {res.duration}")
        print(f"    - Cost: {res.cost}")
        print(f"    - Customer: {res.customer}")
        print(f"    - Recording: {res.hasRecording} | Transcript: {res.hasTranscript} ({len(res.segments)} turns)")

        assert res.provider in ["vapi", "retell", "elevenlabs"]
        if res.score is not None:
            assert res.grade in ["A+", "A", "B", "C", "F"]
        else:
            assert res.grade is None

        # 4. Test Grade Calculator
        assert calculate_grade(98) == "A+"
        assert calculate_grade(92) == "A"
        assert calculate_grade(85) == "B"
        assert calculate_grade(75) == "C"
        assert calculate_grade(55) == "F"
        assert calculate_grade(None) == None
        print("[4] Grade calculations verified")

        print("\nALL CALLS API TESTS PASSED SUCCESSFULLY! ")

    except Exception as e:
        print(f"\n TEST FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_calls_api()
