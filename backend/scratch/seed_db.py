import sys
import os
from datetime import datetime, timedelta, timezone
import random
import uuid

# Add parent dir to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.user import User
from app.models.organization import Organization, Member
from app.models.project import Project
from app.models.agent import Agent
from app.models.conversation import Conversation, SpeechSegment
from app.models.alert import AlertRule, Alert
from app.models.integration import Integration

TRANSCRIPTS_PRESETS = [
    {
        "emotion": "calm",
        "turns": [
            ("agent", "Hello! Thank you for calling Benten support. How can I assist you today?"),
            ("user", "Hi, I'm trying to set up my custom LLM voice pipeline but it keeps timing out."),
            ("agent", "I'd be happy to look into that. Could you share your provider webhook URL?"),
            ("user", "Sure, it is HTTPS api dot benten-demo dot com slash webhook."),
            ("agent", "Thank you. I see a latency spikes of 1.4 seconds from your server. Let me increase the connection timeout."),
            ("user", "Awesome, that resolved it! Thanks for your help."),
            ("agent", "Glad to help! Have a great day.")
        ]
    },
    {
        "emotion": "neutral",
        "turns": [
            ("agent", "Hello, billing department. How can I help you?"),
            ("user", "Hi, I noticed a double charge on my account this month."),
            ("agent", "I apologize for that. Let me look up your billing history. Can you confirm your email?"),
            ("user", "Yes, it is user@example.com."),
            ("agent", "Thanks. I see the duplicate charge. I've initiated a refund which should reflect in 3 business days."),
            ("user", "Perfect, thank you so much for the quick help."),
            ("agent", "You're welcome. Is there anything else I can assist with? No? Have a great day!")
        ]
    },
    {
        "emotion": "frustrated",
        "turns": [
            ("agent", "Welcome to Benten booking line. How can I assist you?"),
            ("user", "I've been trying to book an appointment for 20 minutes and your system keeps crashing."),
            ("agent", "I'm very sorry to hear that. Let me handle the booking manually for you. What day works best?"),
            ("user", "I need Monday morning, around 9 AM if possible."),
            ("agent", "I have 9:30 AM available on Monday. Shall I book that?"),
            ("user", "Yes, please do. This is much faster than your online form."),
            ("agent", "All booked! You should receive a confirmation email shortly. Again, sorry for the technical issues.")
        ]
    },
    {
        "emotion": "neutral",
        "turns": [
            ("agent", "Benten Clinic, how can I help?"),
            ("user", "Hello, I would like to schedule my annual physical checkup."),
            ("agent", "Certainly. We have openings next Thursday afternoon or Friday morning. Which is better?"),
            ("user", "Friday morning is preferred."),
            ("agent", "Great, I have booked you for Friday at 10:00 AM with Dr. Smith."),
            ("user", "Thank you, see you then."),
            ("agent", "Goodbye!")
        ]
    }
]

def seed_database():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            print("No users found in database. Please run or register a user first.")
            return

        print(f"Seeding data for {len(users)} users...")

        for user in users:
            print(f"\n--- Seeding for User: {user.email} ---")
            
            # 1. Ensure Org and Membership
            member = db.query(Member).filter(Member.email == user.email).first()
            if not member:
                org = Organization(name=f"{user.email.split('@')[0]}'s Org")
                db.add(org)
                db.commit()
                db.refresh(org)
                
                member = Member(
                    organization_id=org.id,
                    email=user.email,
                    role="Owner",
                    avatar_url=f"https://i.pravatar.cc/150?u={user.id}"
                )
                db.add(member)
                db.commit()
                db.refresh(member)
            else:
                org = db.query(Organization).filter(Organization.id == member.organization_id).first()

            # Ensure some secondary organization members
            secondary_emails = [f"dev1_{org.id.hex[:4]}@example.com", f"support2_{org.id.hex[:4]}@example.com"]
            for se in secondary_emails:
                existing_member = db.query(Member).filter(Member.organization_id == org.id, Member.email == se).first()
                if not existing_member:
                    new_m = Member(
                        organization_id=org.id,
                        email=se,
                        role="Developer" if "dev" in se else "Viewer",
                        avatar_url=f"https://i.pravatar.cc/150?img={random.randint(1, 70)}"
                    )
                    db.add(new_m)
            db.commit()

            # 2. Ensure Project
            project = db.query(Project).filter(Project.organization_id == org.id).first()
            if not project:
                project = Project(
                    organization_id=org.id,
                    name="Default Project"
                )
                db.add(project)
                db.commit()
                db.refresh(project)

            # Ensure default integration options exist for project
            integration_providers = ["Vapi", "Retell", "ElevenLabs", "OpenAI Realtime API"]
            for ip in integration_providers:
                existing_int = db.query(Integration).filter(
                    Integration.project_id == project.id,
                    Integration.name.ilike(ip)
                ).first()
                if not existing_int:
                    new_int = Integration(
                        project_id=project.id,
                        name=ip,
                        connected=False
                    )
                    db.add(new_int)
            db.commit()

            # Clean existing agents, conversations, alerts, alert rules to reseed cleanly
            print("Cleaning old agents, conversations, and alerts...")
            db.query(Alert).filter(Alert.project_id == project.id).delete()
            db.query(AlertRule).filter(AlertRule.project_id == project.id).delete()
            
            # Get agent IDs for this project to delete speech segments
            agent_ids = [a.id for a in db.query(Agent).filter(Agent.project_id == project.id).all()]
            if agent_ids:
                conv_ids = [c.id for c in db.query(Conversation).filter(Conversation.agent_id.in_(agent_ids)).all()]
                if conv_ids:
                    db.query(SpeechSegment).filter(SpeechSegment.conversation_id.in_(conv_ids)).delete()
                    db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete()
                db.query(Agent).filter(Agent.id.in_(agent_ids)).delete()
            db.commit()

            # 3. Create Agents
            agents_to_create = [
                ("Sales Assistant", "vapi"),
                ("Customer Support", "retell"),
                ("Billing Bot", "elevenlabs"),
                ("Feedback Agent", "vapi")
            ]
            agents = []
            for name, provider in agents_to_create:
                agent = Agent(
                    project_id=project.id,
                    name=name,
                    provider=provider
                )
                db.add(agent)
                db.commit()
                db.refresh(agent)
                agents.append(agent)

            print(f"Created {len(agents)} agents.")

            # 4. Create Alert Rules
            alert_rules = [
                AlertRule(
                    project_id=project.id,
                    metric="Average Latency",
                    threshold="> 800ms",
                    duration="5m",
                    action="Slack Notification"
                ),
                AlertRule(
                    project_id=project.id,
                    metric="Dead Air",
                    threshold="> 15%",
                    duration="2m",
                    action="PagerDuty Incident"
                ),
                AlertRule(
                    project_id=project.id,
                    metric="Voice Quality MOS",
                    threshold="< 3.5",
                    duration="10m",
                    action="Email Alert"
                )
            ]
            for ar in alert_rules:
                db.add(ar)
            db.commit()
            print(f"Created {len(alert_rules)} alert rules.")

            # 5. Create Conversations & Speech Segments over the last 10 days
            total_conversations = 25
            now = datetime.now(timezone.utc)
            conversations = []

            for i in range(total_conversations):
                # Distribute timestamps
                days_ago = random.uniform(0, 10)
                created_at = now - timedelta(days=days_ago)

                agent = random.choice(agents)
                preset = random.choice(TRANSCRIPTS_PRESETS)

                # Generate scores depending on provider name and random factors
                if agent.provider == "vapi":
                    latency = random.randint(700, 1100)
                    dead_air = random.uniform(5.0, 12.0)
                    voice_quality = random.randint(70, 85)
                    interruptions = random.randint(1, 4)
                elif agent.provider == "retell":
                    latency = random.randint(350, 500)
                    dead_air = random.uniform(1.5, 4.0)
                    voice_quality = random.randint(88, 96)
                    interruptions = random.randint(0, 2)
                else:
                    latency = random.randint(400, 600)
                    dead_air = random.uniform(2.5, 6.0)
                    voice_quality = random.randint(80, 92)
                    interruptions = random.randint(0, 3)

                # Apply penalty for health score
                health_score = 100 - int(latency / 20) - int(dead_air * 2) - (interruptions * 4)
                health_score = max(30, min(100, health_score))

                status_val = "Healthy"
                if health_score < 70:
                    status_val = "Critical"
                elif health_score < 85:
                    status_val = "Warning"

                duration_sec = random.randint(45, 300)

                conv = Conversation(
                    project_id=project.id,
                    agent_id=agent.id,
                    duration_sec=duration_sec,
                    status="Completed",
                    health_score=health_score,
                    latency_ms=latency,
                    dead_air_percent=round(dead_air, 2),
                    interruptions=interruptions,
                    speech_rate_wpm=random.randint(110, 150),
                    voice_quality=voice_quality,
                    primary_emotion=preset["emotion"],
                    audio_url="http://localhost:8000/static/audio/sample.wav",
                    raw_metrics_json={
                        "provider": agent.provider,
                        "ingestion_method": "webhook",
                        "device": "webbrowser"
                    },
                    created_at=created_at
                )
                db.add(conv)
                db.commit()
                db.refresh(conv)
                conversations.append(conv)

                # Save turns as SpeechSegments
                time_step = duration_sec / (len(preset["turns"]) + 1)
                current_time = 0.0

                for speaker, text in preset["turns"]:
                    start = current_time + random.uniform(0.1, 0.5)
                    end = start + len(text.split()) * 0.4 # approx speech duration
                    current_time = end

                    segment = SpeechSegment(
                        conversation_id=conv.id,
                        speaker=speaker,
                        start_sec=round(start, 2),
                        end_sec=round(end, 2),
                        text=text,
                        created_at=created_at
                    )
                    db.add(segment)
                db.commit()

            print(f"Created {len(conversations)} conversations and segments.")

            # 6. Create Triggered/Resolved Alerts based on conversation results
            # Select conversations with low scores/high latencies to trigger alerts
            critical_convs = [c for c in conversations if c.health_score < 75]
            triggered_count = 0
            for idx, c in enumerate(critical_convs):
                # Pick rule
                rule = alert_rules[idx % len(alert_rules)]
                
                # Alternate between Triggered and Recovered
                alert_status = "Triggered" if idx % 2 == 0 else "Recovered"
                
                alert = Alert(
                    project_id=project.id,
                    alert_rule_id=rule.id,
                    conversation_id=c.id,
                    status=alert_status,
                    triggered_at=c.created_at + timedelta(seconds=30),
                    resolved_at=c.created_at + timedelta(minutes=5) if alert_status == "Recovered" else None
                )
                db.add(alert)
                triggered_count += 1
            db.commit()
            print(f"Created {triggered_count} triggered alerts.")

        print("\nAll database seeding completed successfully!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
