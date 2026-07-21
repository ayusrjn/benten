import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.pipeline.extractors import calculate_detailed_interruptions, calculate_interruptions

def test_calculate_detailed_interruptions():
    segments = [
        {"start": 0.0, "end": 3.5, "role": "agent", "text": "Hello, how can I help you today?"},
        # User interrupts agent at t=3.0s, agent stops at t=3.5s (barge-in accepted)
        {"start": 3.0, "end": 7.0, "role": "user", "text": "Hi I need help with my bill"},
        {"start": 7.5, "end": 12.0, "role": "agent", "text": "Sure, I can check your account balance."},
        # User interrupts agent at t=9.0s, agent continues until t=12.0s (barge-in ignored / double talk)
        {"start": 9.0, "end": 11.0, "role": "user", "text": "Wait wait listen to me"},
        # AI interrupts user at t=14.0s while user talks from 13.0 to 16.0s
        {"start": 13.0, "end": 16.0, "role": "user", "text": "My customer ID is 12345"},
        {"start": 14.0, "end": 18.0, "role": "agent", "text": "Got it, let me search that"}
    ]

    call_duration = 20.0
    details = calculate_detailed_interruptions(segments, call_duration)
    total_legacy = calculate_interruptions(segments, call_duration)

    print("Test Results:")
    for k, v in details.items():
        print(f"  {k}: {v}")

    assert details["user_to_ai_interruptions"] == 2, f"Expected 2 User->AI, got {details['user_to_ai_interruptions']}"
    assert details["ai_to_user_interruptions"] == 1, f"Expected 1 AI->User, got {details['ai_to_user_interruptions']}"
    assert details["total_interruption_events"] == 3, f"Expected 3 total, got {details['total_interruption_events']}"
    assert details["barge_ins_accepted"] == 1, f"Expected 1 accepted, got {details['barge_ins_accepted']}"
    assert details["barge_ins_ignored"] == 1, f"Expected 1 ignored, got {details['barge_ins_ignored']}"
    assert total_legacy == 3, f"Expected legacy count 3, got {total_legacy}"
    print("All assertion tests passed successfully!")

if __name__ == "__main__":
    test_calculate_detailed_interruptions()
