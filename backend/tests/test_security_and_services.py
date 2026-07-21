import pytest
from app.api.security_crypto import encrypt_secret, decrypt_secret
from app.services.project_service import ProjectService
from app.services.integration_service import IntegrationService
from app.services.conversation_service import ConversationService, format_duration, calculate_grade
from app.models.conversation import Conversation, SpeechSegment


def test_encryption_decryption_roundtrip():
    raw = "sk_test_vapi_1234567890abcdef"
    encrypted = encrypt_secret(raw)
    assert encrypted != raw
    assert encrypted.startswith("gAAAAA")

    decrypted = decrypt_secret(encrypted)
    assert decrypted == raw


def test_mask_api_key():
    raw = "sk_test_1234567890"
    masked = IntegrationService.mask_api_key(raw)
    assert "7890" in masked
    assert "sk_test" not in masked


def test_duration_formatting():
    assert format_duration(0) == "0s"
    assert format_duration(45) == "45s"
    assert format_duration(60) == "1m"
    assert format_duration(125) == "2m 5s"


def test_grade_calculation():
    assert calculate_grade(98) == "A+"
    assert calculate_grade(92) == "A"
    assert calculate_grade(85) == "B"
    assert calculate_grade(75) == "C"
    assert calculate_grade(65) == "F"
    assert calculate_grade(None) is None


def test_project_service_provisioning(db_session, test_user):
    project = ProjectService.get_or_create_user_project(db_session, test_user)
    assert project is not None
    assert project.name == "Default Project"

    # Secondary call should be idempotent and return same project
    project2 = ProjectService.get_or_create_user_project(db_session, test_user)
    assert project2.id == project.id
