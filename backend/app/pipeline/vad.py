import logging
import torch
import numpy as np
from typing import List, Dict

logger = logging.getLogger(__name__)

_vad_instance = None


def get_vad() -> "SileroVADWrapper":
    """Returns the singleton SileroVADWrapper, creating it on first call."""
    global _vad_instance
    if _vad_instance is None:
        _vad_instance = SileroVADWrapper()
    return _vad_instance


def preload_vad():
    """Eagerly initialize the VAD model (called at worker startup)."""
    get_vad()


class SileroVADWrapper:
    """
    ONNX wrapper class for Silero VAD model to perform voice activity detection.
    """
    def __init__(self, model_path: str = None):
        logger.info("Initializing Silero VAD Wrapper")
        self.model_path = model_path
        self.model, self.utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=True,
            trust_repo=True
        )
        self.get_speech_ts = self.utils[0]

    def get_speech_timestamps(self, audio_np: np.ndarray, sample_rate: int = 16000) -> List[Dict[str, float]]:
        """
        Processes audio array and returns active speech intervals.
        Returns:
            List[Dict[str, float]]: List of dicts like {'start': float, 'end': float} in seconds.
        """
        logger.info("Running VAD on audio stream")
        if audio_np.ndim > 1:
            audio_np = np.mean(audio_np, axis=1)
            
        audio_tensor = torch.from_numpy(audio_np).float()

        speech_timestamps = self.get_speech_ts(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate
        )
        
        return [
            {
                'start': ts['start'] / sample_rate,
                'end': ts['end'] / sample_rate
            }
            for ts in speech_timestamps
        ]
