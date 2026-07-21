import logging
import os
from typing import List, Dict, Any

import numpy as np
import torch

from app.config import settings

try:
    from pyannote.audio import Pipeline
except ImportError:
    Pipeline = None

logger = logging.getLogger(__name__)

# Module-level singleton — shared across all tasks in the same worker process
_diarizer_instance = None

def get_diarizer() -> "PyAnnoteDiarizer":
    """Returns the singleton PyAnnoteDiarizer, creating it on first call."""
    global _diarizer_instance
    if _diarizer_instance is None:
        _diarizer_instance = PyAnnoteDiarizer()
    return _diarizer_instance

def preload_diarizer():
    """Eagerly initialize the diarizer (called at worker startup)."""
    get_diarizer()


class PyAnnoteDiarizer:
    """
    Speaker diarization wrapper for pyannote.audio 4.x
    """

    def __init__(self, auth_token: str = None):
        logger.info("Initializing Speaker Diarizer")

        self.auth_token = (
            auth_token
            or getattr(settings, "HF_AUTH_TOKEN", None)
            or os.environ.get("HF_AUTH_TOKEN")
            or os.environ.get("HF_TOKEN")
        )

        self.pipeline = None

        if Pipeline is None:
            logger.warning("pyannote.audio is not installed.")
            return

        if not self.auth_token:
            logger.warning("HF token not provided.")
            return

        # Ensure HF_TOKEN is in os.environ for PyAnnote and Hugging Face Hub requests
        os.environ["HF_TOKEN"] = self.auth_token
        os.environ["HUGGING_FACE_HUB_TOKEN"] = self.auth_token

        # PyTorch 2.6+ weights_only safe globals fix for PyAnnote checkpoint loading
        if hasattr(torch.serialization, "add_safe_globals"):
            try:
                from torch.torch_version import TorchVersion
                torch.serialization.add_safe_globals([TorchVersion])
            except Exception:
                pass

        try:
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=self.auth_token,
            )

            if torch.cuda.is_available():
                self.pipeline.to(torch.device("cuda"))

            logger.info("PyAnnote pipeline initialized.")

        except Exception:
            logger.exception("Failed to initialize PyAnnote pipeline")

    def diarize_mono(
        self,
        audio_np: np.ndarray,
        sample_rate: int = 16000,
    ) -> List[Dict[str, Any]]:
        """
        Runs speaker diarization and maps first speaker to Agent.
        """

        if self.pipeline is None:
            return []

        if audio_np.ndim > 1:
            audio_np = np.mean(audio_np, axis=1)

        waveform = (
            torch.from_numpy(audio_np)
            .float()
            .unsqueeze(0)
        )

        try:
            output = self.pipeline(
                {
                    "waveform": waveform,
                    "sample_rate": sample_rate,
                },
                num_speakers=2,
            )

        except Exception:
            logger.exception("PyAnnote inference failed")
            return []

        #
        # pyannote.audio 4.x
        #
        diarization = output.speaker_diarization

        segments = []

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                {
                    "start": float(turn.start),
                    "end": float(turn.end),
                    "speaker_id": speaker,
                }
            )

        if not segments:
            return []

        segments.sort(key=lambda x: x["start"])

        first_speaker = segments[0]["speaker_id"]

        for seg in segments:
            seg["role"] = (
                "Agent"
                if seg["speaker_id"] == first_speaker
                else "User"
            )

        return segments

    def diarize_stereo(
        self,
        left_channel: np.ndarray,
        right_channel: np.ndarray,
        sample_rate: int = 16000,
        vad_wrapper=None,
    ) -> List[Dict[str, Any]]:
        """
        Direct channel mapping for stereo recordings.
        """

        if vad_wrapper is None:
            return []

        segments = []

        for ts in vad_wrapper.get_speech_timestamps(
            left_channel,
            sample_rate,
        ):
            segments.append(
                {
                    "start": ts["start"],
                    "end": ts["end"],
                    "role": "Agent",
                    "speaker_id": "Channel_0",
                }
            )

        for ts in vad_wrapper.get_speech_timestamps(
            right_channel,
            sample_rate,
        ):
            segments.append(
                {
                    "start": ts["start"],
                    "end": ts["end"],
                    "role": "User",
                    "speaker_id": "Channel_1",
                }
            )

        segments.sort(key=lambda x: x["start"])
        return segments