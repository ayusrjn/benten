import logging
import numpy as np
from typing import Dict, Any

try:
    from transformers import pipeline
except ImportError:
    pipeline = None

logger = logging.getLogger(__name__)

_sentiment_pipeline = None
_nisqa_model = None

try:
    import torch
    from torchmetrics.audio import NonIntrusiveSpeechQualityAssessment
except ImportError:
    torch = None
    NonIntrusiveSpeechQualityAssessment = None


def get_nisqa_model():
    """Lazy-loads singleton PyTorch TorchMetrics NISQA model."""
    global _nisqa_model
    if _nisqa_model is None and NonIntrusiveSpeechQualityAssessment is not None:
        try:
            logger.info("Loading NISQA speech quality assessment model")
            _nisqa_model = NonIntrusiveSpeechQualityAssessment(fs=16000)
        except Exception as e:
            logger.error(f"Failed to load NISQA model: {e}")
    return _nisqa_model


def preload_nisqa():
    """Eagerly initialize the NISQA model (called at worker startup)."""
    get_nisqa_model()


def get_sentiment_pipeline():
    global _sentiment_pipeline
    if _sentiment_pipeline is None and pipeline is not None:
        try:
            logger.info("Loading RoBERTa sentiment model")
            _sentiment_pipeline = pipeline(
                "text-classification",
                model="SamLowe/roberta-base-go_emotions",
                top_k=3,
                truncation=True,
                max_length=512
            )
        except Exception as e:
            logger.error(f"Failed to load sentiment pipeline: {e}")
    return _sentiment_pipeline

def preload_sentiment():
    """Eagerly initialize the sentiment pipeline (called at worker startup)."""
    get_sentiment_pipeline()

def score_sentiment_roberta(transcript_text: str) -> Dict[str, float]:
    """
    Passes textual transcript turns through RoBERTa-go-emotions for sentiment classification.
    """
    logger.info("Running RoBERTa sentiment analysis")
    if not transcript_text.strip():
        return {}
        
    classifier = get_sentiment_pipeline()
    if classifier is None:
        return {"neutral": 1.0}
        
    try:
        # classifier returns a list of lists when top_k is specified
        results = classifier(transcript_text)
        if isinstance(results, list) and len(results) > 0:
            if isinstance(results[0], list):
                results = results[0]
        return {item['label']: float(item['score']) for item in results}
    except Exception as e:
        logger.error(f"Error during sentiment analysis: {e}")
        return {"neutral": 1.0}

def score_voice_quality_nisqa(audio_np: np.ndarray, sample_rate: int = 16000) -> float:
    """
    Evaluates speech quality using NISQA to output Mean Opinion Score (MOS) between 1.0 and 5.0.
    """
    logger.info("Running NISQA voice quality analysis")
    nisqa = get_nisqa_model()
    if nisqa is None or torch is None:
        logger.warning("NISQA model not available, using default fallback score (4.0)")
        return 4.0

    try:
        # Ensure 1D audio waveform
        if audio_np.ndim > 1:
            audio_np = np.mean(audio_np, axis=1)

        # Convert to 2D tensor (batch_size=1, time_steps)
        audio_tensor = torch.from_numpy(audio_np).float()
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor.unsqueeze(0)

        with torch.no_grad():
            res = nisqa(audio_tensor)
            # res[0] is overall predicted MOS
            mos_raw = float(res[0].item() if hasattr(res[0], 'item') else res[0])
            mos_score = max(1.0, min(5.0, round(mos_raw, 2)))
            logger.info(f"NISQA MOS score calculated: {mos_score}")
            return mos_score
    except Exception as e:
        logger.error(f"Error during NISQA voice quality evaluation: {e}")
        return 4.0

