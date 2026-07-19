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
        
    # Sort by start time
    sorted_segments = sorted(speech_segments, key=lambda x: x["start"])
    
    # Merge overlapping segments
    merged = []
    current_start = sorted_segments[0]["start"]
    current_end = sorted_segments[0]["end"]
    
    for seg in sorted_segments[1:]:
        if seg["start"] <= current_end:
            current_end = max(current_end, seg["end"])
        else:
            merged.append((current_start, current_end))
            current_start = seg["start"]
            current_end = seg["end"]
    merged.append((current_start, current_end))
    
    total_dead_air = 0.0
    
    # Check gap before first segment
    if merged[0][0] > 1.5:
        total_dead_air += merged[0][0]
        
    # Check gaps between segments
    for i in range(1, len(merged)):
        gap = merged[i][0] - merged[i-1][1]
        if gap > 1.5:
            total_dead_air += gap
            
    # Check gap after last segment
    if call_duration - merged[-1][1] > 1.5:
        total_dead_air += call_duration - merged[-1][1]
        
    return (total_dead_air / call_duration) * 100.0

def calculate_interruptions(speech_segments: List[Dict[str, Any]]) -> int:
    """
    Calculates the frequency of overlap blocks (where user talks over the agent).
    """
    logger.debug("Calculating agent interruption count")
    interruptions = 0
    
    agent_segments = [s for s in speech_segments if s.get("role") == "Agent"]
    user_segments = [s for s in speech_segments if s.get("role") == "User"]
    
    for agent_seg in agent_segments:
        for user_seg in user_segments:
            # Check if user segment starts during agent segment
            if agent_seg["start"] < user_seg["start"] < agent_seg["end"]:
                interruptions += 1
                
    return interruptions

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
