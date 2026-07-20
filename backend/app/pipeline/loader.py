import io
import logging
import requests
import numpy as np
import pyloudnorm as pyln
import torchaudio
from typing import BinaryIO, Tuple

logger = logging.getLogger(__name__)

import os

def download_audio_stream(audio_url: str) -> io.BytesIO:
    """
    Downloads audio from the given URL into an in-memory buffer.
    Supports relative /static/ paths by attempting local disk read first.
    """
    logger.info(f"Downloading audio stream from: {audio_url}")
    if not audio_url:
        raise ValueError("Audio URL is empty or not available")

    # Handle relative static paths
    if audio_url.startswith("/static/"):
        storage_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "storage", "audio"))
        filename = os.path.basename(audio_url)
        local_filepath = os.path.join(storage_dir, filename)

        if os.path.exists(local_filepath):
            logger.info(f"Loading static audio directly from local file: {local_filepath}")
            with open(local_filepath, "rb") as f:
                return io.BytesIO(f.read())
        else:
            # Fallback to local server HTTP request
            audio_url = f"http://localhost:8000{audio_url}"

    response = requests.get(audio_url, stream=True, timeout=30)
    response.raise_for_status()
    buffer = io.BytesIO()
    for chunk in response.iter_content(chunk_size=8192):
        buffer.write(chunk)
    buffer.seek(0)
    return buffer

def load_and_resample_audio(audio_data: BinaryIO, target_sample_rate: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Decodes and resamples the incoming audio data to the target sample rate.
    """
    logger.info(f"Resampling audio to {target_sample_rate}Hz")
    waveform, sample_rate = torchaudio.load(audio_data)
    
    if sample_rate != target_sample_rate:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=target_sample_rate)
        waveform = resampler(waveform)
        
    # Shape for pyloudnorm: (time, channels)
    audio_np = waveform.numpy().T
    return audio_np, target_sample_rate

def normalize_loudness(audio_np: np.ndarray, sample_rate: int, target_lufs: float = -23.0) -> np.ndarray:
    """
    Applies EBU R128 loudness normalization to the audio array.
    """
    logger.info(f"Normalizing audio loudness to {target_lufs} LUFS")
    meter = pyln.Meter(sample_rate)
    try:
        loudness = meter.integrated_loudness(audio_np)
        normalized_audio = pyln.normalize.loudness(audio_np, loudness, target_lufs)
        return normalized_audio
    except Exception as e:
        logger.warning(f"Loudness normalization failed: {e}")
        return audio_np
