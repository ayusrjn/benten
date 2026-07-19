import logging
import torch
import numpy as np
import os
from typing import List, Dict, Any

try:
    from pyannote.audio import Pipeline
except ImportError:
    Pipeline = None

logger = logging.getLogger(__name__)

class PyAnnoteDiarizer:
    """
    Wrapper for speaker diarization using PyAnnote pipeline.
    """
    def __init__(self, auth_token: str = None):
        logger.info("Initializing Speaker Diarizer")
        self.auth_token = auth_token or os.environ.get("HF_AUTH_TOKEN")
        if Pipeline is not None and self.auth_token:
            try:
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.auth_token
                )
                if torch.cuda.is_available():
                    self.pipeline.to(torch.device("cuda"))
            except Exception as e:
                logger.error(f"Failed to load PyAnnote pipeline: {e}")
                self.pipeline = None
        else:
            logger.warning("PyAnnote Pipeline missing token or package. Diarization will be mocked.")
            self.pipeline = None

    def diarize_mono(self, audio_np: np.ndarray, sample_rate: int = 16000) -> List[Dict[str, Any]]:
        """
        Runs clustering and maps speaker embeddings to User vs Agent using the initial greeting heuristic.
        """
        logger.info("Running mono speaker diarization")
        if self.pipeline is None:
            return []
            
        if len(audio_np.shape) > 1 and audio_np.shape[1] > 1:
            audio_np = np.mean(audio_np, axis=1)
            
        audio_tensor = torch.from_numpy(audio_np).float().unsqueeze(0)
        
        try:
            diarization = self.pipeline({"waveform": audio_tensor, "sample_rate": sample_rate})
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return []
            
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append({
                "start": float(turn.start),
                "end": float(turn.end),
                "speaker_id": speaker
            })
            
        if not segments:
            return []
            
        segments.sort(key=lambda x: x["start"])
        first_speaker = segments[0]["speaker_id"]
        
        for seg in segments:
            seg["role"] = "Agent" if seg["speaker_id"] == first_speaker else "User"
            
        return segments

    def diarize_stereo(self, left_channel: np.ndarray, right_channel: np.ndarray, sample_rate: int = 16000, vad_wrapper=None) -> List[Dict[str, Any]]:
        """
        Performs direct channel mapping for stereo streams.
        """
        logger.info("Mapping stereo channels to speakers")
        segments = []
        if vad_wrapper:
            left_ts = vad_wrapper.get_speech_timestamps(left_channel, sample_rate)
            right_ts = vad_wrapper.get_speech_timestamps(right_channel, sample_rate)
            
            for ts in left_ts:
                segments.append({"start": ts["start"], "end": ts["end"], "role": "Agent", "speaker_id": "Channel_0"})
            for ts in right_ts:
                segments.append({"start": ts["start"], "end": ts["end"], "role": "User", "speaker_id": "Channel_1"})
                
            segments.sort(key=lambda x: x["start"])
        return segments
