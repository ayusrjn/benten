from datetime import datetime, timedelta, timezone
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.user import User
from app.services.project_service import ProjectService


def add_call(db, project, days=0, status='Completed', quality=None, latency=0):
    agent = Agent(project_id=project.id, name='Test agent', provider='vapi')
    db.add(agent)
    db.flush()
    db.add(Conversation(project_id=project.id, agent_id=agent.id, provider='vapi',
        status=status, voice_quality=quality, latency_ms=latency, duration_sec=60,
        interruptions=0, dead_air_percent=0,
        created_at=datetime.now(timezone.utc)-timedelta(days=days)))
    db.commit()


def test_empty(client, auth_headers):
    response = client.get('/api/v1/dashboard/metrics', headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data['conversationsCount'] == data['interruptionsCount'] == 0
    for field in ('latencyAvg','deadAirAvg','voiceQualityAvg','avgDurationSec'):
        assert data[field] is None
    for field in ('latencyTrend','volumeTrend','volumeDates'):
        assert data[field] == []


def test_zero(client, auth_headers, db_session, test_user):
    project = ProjectService.get_or_create_user_project(db_session, test_user)
    add_call(db_session, project, quality=0)
    data = client.get('/api/v1/dashboard/metrics', headers=auth_headers).json()
    assert data['voiceQualityAvg'] == data['latencyAvg'] == data['deadAirAvg'] == 0
    assert data['latencyTrend'] == [0]
    assert data['volumeTrend'] == [0,0,0,0,0,0,1]


def test_real_data_and_isolation(client, auth_headers, db_session, test_user):
    project = ProjectService.get_or_create_user_project(db_session, test_user)
    add_call(db_session, project, days=6, quality=80, latency=200)
    add_call(db_session, project, quality=100, latency=400)
    add_call(db_session, project, status='Processing', quality=10)
    other = User(email='other@example.com', hashed_password='unused', is_active=True)
    db_session.add(other)
    db_session.commit()
    other_project = ProjectService.get_or_create_user_project(db_session, other)
    add_call(db_session, other_project, quality=0, latency=9999)
    data = client.get('/api/v1/dashboard/metrics', headers=auth_headers).json()
    assert data['conversationsCount'] == 2
    assert data['voiceQualityAvg'] == 90
    assert data['latencyAvg'] == 300
    assert data['latencyTrend'] == [200,400]
    assert data['volumeTrend'] == [1,0,0,0,0,0,2]
    assert data['volumeDates'][-1] == datetime.now(timezone.utc).date().isoformat()
    assert client.get(f'/api/v1/dashboard/metrics?projectId={other_project.id}', headers=auth_headers).status_code == 403


def test_old_call_and_missing_quality(client, auth_headers, db_session, test_user):
    project = ProjectService.get_or_create_user_project(db_session, test_user)
    add_call(db_session, project, days=8)
    data = client.get('/api/v1/dashboard/metrics', headers=auth_headers).json()
    assert data['conversationsCount'] == 1
    assert data['voiceQualityAvg'] is None
    assert data['volumeTrend'] == data['volumeDates'] == []
