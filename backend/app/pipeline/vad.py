import logging
import torch
import numpy as np
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

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
        # Ensure audio is 1D (mono)
        if len(audio_np.shape) > 1 and audio_np.shape[1] > 1:
            audio_np = np.mean(audio_np, axis=1)
            
        audio_tensor = torch.from_numpy(audio_np).float()
        if audio_tensor.ndim > 1:
            audio_tensor = audio_tensor.squeeze()

        speech_timestamps = self.get_speech_ts(
            audio_tensor,
            self.model,
            sampling_rate=sample_rate
        )
        
        formatted_timestamps = []
        for ts in speech_timestamps:
            formatted_timestamps.append({
                'start': ts['start'] / sample_rate,
                'end': ts['end'] / sample_rate
            })
            
        return formatted_timestamps
