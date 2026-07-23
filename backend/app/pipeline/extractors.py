import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def calculate_turn_latency(speech_segments: List[Dict[str, Any]]) -> float:
    """
    Calculates average agent response latency: t_agent_speech_start - t_user_speech_end.
    """
    logger.debug("Calculating turn latency")
    latencies = []
    
    # Sort segments by start time
    sorted_segments = sorted(speech_segments, key=lambda x: x["start"])
    
    last_user_end = None
    
    for seg in sorted_segments:
        role = seg.get("role")
        if role == "User":
            last_user_end = seg["end"]
        elif role == "Agent" and last_user_end is not None:
            latency = seg["start"] - last_user_end
            if latency > 0:
                latencies.append(latency)
            last_user_end = None  # Reset to calculate only direct responses
            
    if not latencies:
        return 0.0
    return sum(latencies) / len(latencies)

def calculate_dead_air(speech_segments: List[Dict[str, Any]], call_duration: float) -> float:
    """
    Calculates percentage of call length with total silence gaps > 1.5 seconds.
    """
    logger.debug("Calculating dead air percentage")
    if not speech_segments or call_duration <= 0:
        return 0.0

    sorted_segments = sorted(speech_segments, key=lambda x: x["start"])
    merged = []
    current_start = sorted_segments[0]["start"]
    current_end = sorted_segments[0]["end"]

    for seg in sorted_segments[1:]:
        if seg["start"] <= current_end:
            current_end = max(current_end, seg["end"])
        else:
            merged.append((current_start, current_end))
            current_start, current_end = seg["start"], seg["end"]
    merged.append((current_start, current_end))

    total_dead_air = 0.0
    last_end = 0.0

    for start, end in merged:
        gap = start - last_end
        if gap > 1.5:
            total_dead_air += gap
        last_end = end

    gap_end = call_duration - last_end
    if gap_end > 1.5:
        total_dead_air += gap_end

    return (total_dead_air / call_duration) * 100.0

def _normalize_role(role_or_speaker: str) -> str:
    if not role_or_speaker:
        return "user"
    r = str(role_or_speaker).lower()
    if r in ["agent", "bot", "assistant", "channel_0"]:
        return "agent"
    return "user"


def _get_seg_times(seg: Dict[str, Any]) -> tuple:
    start = float(seg.get("start", seg.get("start_sec", 0.0)))
    end = float(seg.get("end", seg.get("end_sec", 0.0)))
    role = _normalize_role(seg.get("role") or seg.get("speaker") or "")
    return start, end, role


def calculate_detailed_interruptions(speech_segments: List[Dict[str, Any]], call_duration: float = 0.0) -> Dict[str, Any]:
    """
    Calculates comprehensive real-data interruption & barge-in telemetry metrics:
      - user_to_ai_interruptions: User interrupted AI
      - ai_to_user_interruptions: AI interrupted User
      - total_interruption_events: Total overlap events
      - avg_overlap_duration_sec: Average duration of overlap (sec)
      - longest_interruption_sec: Max single overlap duration (sec)
      - interruptions_per_minute: Events per minute
      - barge_ins_accepted: User interrupted AI and AI backed off (stopped in <= 800ms)
      - barge_ins_ignored: User interrupted AI and AI kept talking (> 800ms)
    """
    logger.debug("Calculating detailed real-data interruption metrics")
    user_to_ai = 0
    ai_to_user = 0
    barge_ins_accepted = 0
    barge_ins_ignored = 0
    overlap_durations = []
    events = []

    norm_segments = []
    for s in speech_segments:
        start, end, role = _get_seg_times(s)
        if end > start:
            norm_segments.append({"start": start, "end": end, "role": role})

    norm_segments.sort(key=lambda x: x["start"])

    for i in range(len(norm_segments)):
        seg_i = norm_segments[i]
        for j in range(i + 1, len(norm_segments)):
            seg_j = norm_segments[j]

            if seg_j["start"] >= seg_i["end"]:
                break

            if seg_i["role"] != seg_j["role"]:
                overlap_start = max(seg_i["start"], seg_j["start"])
                overlap_end = min(seg_i["end"], seg_j["end"])
                overlap_dur = overlap_end - overlap_start

                if overlap_dur > 0:
                    overlap_dur_rounded = round(overlap_dur, 2)
                    overlap_durations.append(overlap_dur_rounded)

                    interrupted_role = seg_i["role"]
                    interrupter_role = seg_j["role"]

                    barge_in_status = None
                    if interrupter_role == "user" and interrupted_role == "agent":
                        event_type = "user_to_ai"
                        user_to_ai += 1
                        agent_remaining = seg_i["end"] - seg_j["start"]
                        if agent_remaining <= 0.8:
                            barge_ins_accepted += 1
                            barge_in_status = "accepted"
                        else:
                            barge_ins_ignored += 1
                            barge_in_status = "ignored"
                    else:
                        event_type = "ai_to_user"
                        ai_to_user += 1

                    events.append({
                        "start": round(overlap_start, 2),
                        "end": round(overlap_end, 2),
                        "duration": overlap_dur_rounded,
                        "interrupter": interrupter_role,
                        "interrupted": interrupted_role,
                        "type": event_type,
                        "barge_in_status": barge_in_status
                    })

    total_events = user_to_ai + ai_to_user
    avg_overlap = round(sum(overlap_durations) / len(overlap_durations), 2) if overlap_durations else 0.0
    longest_overlap = round(max(overlap_durations), 2) if overlap_durations else 0.0

    if not call_duration or call_duration <= 0:
        if norm_segments:
            call_duration = max(s["end"] for s in norm_segments)

    call_dur_min = (call_duration / 60.0) if call_duration > 0 else 0.0
    rate_per_min = round(total_events / call_dur_min, 2) if call_dur_min > 0 else 0.0

    return {
        "user_to_ai_interruptions": user_to_ai,
        "ai_to_user_interruptions": ai_to_user,
        "total_interruption_events": total_events,
        "avg_overlap_duration_sec": avg_overlap,
        "longest_interruption_sec": longest_overlap,
        "interruptions_per_minute": rate_per_min,
        "barge_ins_accepted": barge_ins_accepted,
        "barge_ins_ignored": barge_ins_ignored,
        "events": events
    }


def calculate_interruptions(speech_segments: List[Dict[str, Any]], call_duration: float = 0.0) -> int:
    """
    Calculates total frequency of overlap events.
    """
    details = calculate_detailed_interruptions(speech_segments, call_duration)
    return details["total_interruption_events"]

def calculate_speech_rate(speech_segments: List[Dict[str, Any]]) -> float:
    """
    Calculates average word rate per active turn duration in minutes (WPM).
    Requires 'text' key in segments if transcript is available.
    """
    logger.debug("Calculating speech rate (WPM)")
    total_words = 0
    total_duration_sec = 0.0
    
    for seg in speech_segments:
        text = seg.get("text", "")
        if text:
            words = len(text.split())
            total_words += words
            total_duration_sec += (seg["end"] - seg["start"])
            
    if total_duration_sec == 0:
        return 0.0
        
    duration_min = total_duration_sec / 60.0
    return total_words / duration_min
